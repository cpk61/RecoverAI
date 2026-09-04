from __future__ import annotations
from pathlib import Path
import json, math, random
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / 'data'
ARTIFACT_DIR = BASE / 'artifacts'
DATA_DIR.mkdir(exist_ok=True)
ARTIFACT_DIR.mkdir(exist_ok=True)

FAILURES = ['network_error','insufficient_funds','bank_declined','expired_card','auth_failed','checkout_abandoned']
CHANNELS = ['card','upi','netbanking','wallet']
SEGMENTS = ['new','repeat','vip']


def sigmoid(x: float) -> float:
    return 1/(1+math.exp(-x))


def build_synthetic_dataset(n: int = 650, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    rows=[]
    for i in range(n):
        amount = round(rng.uniform(199, 25000),2)
        failure = rng.choices(FAILURES, weights=[18,22,18,9,12,21])[0]
        channel = rng.choice(CHANNELS)
        segment = rng.choices(SEGMENTS, weights=[45,45,10])[0]
        previous_successes = max(0, int(rng.gauss(3 if segment=='repeat' else 1, 2)))
        if segment=='vip': previous_successes += rng.randint(4,10)
        retry_count = rng.randint(0,3)
        hours_since_failure = round(rng.uniform(0.1,72),1)
        score = -0.7
        score += 0.22*min(previous_successes,10)
        score -= 0.55*retry_count
        score -= 0.000045*min(amount,12000)
        score += {'network_error':1.2,'checkout_abandoned':0.65,'insufficient_funds':0.1,'auth_failed':-0.2,'bank_declined':-0.65,'expired_card':-0.8}[failure]
        score += {'vip':0.8,'repeat':0.35,'new':-0.2}[segment]
        score += 0.22 if channel=='upi' else 0
        score -= 0.006*hours_since_failure
        prob = sigmoid(score)
        recovered = 1 if rng.random() < prob else 0
        rows.append({
            'payment_id':f'pay_demo_{i+1:04d}', 'amount':amount, 'failure_reason':failure,
            'channel':channel, 'customer_segment':segment, 'previous_successes':previous_successes,
            'retry_count':retry_count,'hours_since_failure':hours_since_failure,'recovered':recovered
        })
    df=pd.DataFrame(rows)
    df.to_csv(DATA_DIR/'synthetic_failures.csv',index=False)
    return df


def train_model(df: pd.DataFrame):
    features=['amount','failure_reason','channel','customer_segment','previous_successes','retry_count','hours_since_failure']
    X=df[features]
    y=df['recovered']
    X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=0.25,random_state=42,stratify=y)
    cat=['failure_reason','channel','customer_segment']
    num=['amount','previous_successes','retry_count','hours_since_failure']
    pre=ColumnTransformer([
        ('cat',OneHotEncoder(handle_unknown='ignore'),cat),
        ('num',StandardScaler(),num)
    ])
    pipe=Pipeline([('pre',pre),('model',LogisticRegression(max_iter=1000,class_weight='balanced'))])
    pipe.fit(X_train,y_train)
    pred=pipe.predict(X_test)
    proba=pipe.predict_proba(X_test)[:,1]
    metrics={
        'accuracy':round(float(accuracy_score(y_test,pred)),3),
        'precision':round(float(precision_score(y_test,pred,zero_division=0)),3),
        'recall':round(float(recall_score(y_test,pred,zero_division=0)),3),
        'roc_auc':round(float(roc_auc_score(y_test,proba)),3),
        'test_rows':int(len(y_test))
    }
    (ARTIFACT_DIR/'metrics.json').write_text(json.dumps(metrics,indent=2))
    return pipe, metrics


def policy(row: pd.Series, p: float):
    reason=row['failure_reason']; retries=int(row['retry_count'])
    if retries >= 3:
        return ('STOP_AND_ESCALATE','Retry ceiling reached; avoid repeated customer/payment pressure.',0.0,True)
    if p < 0.20:
        return ('HUMAN_REVIEW','Low model confidence of recovery; route to human review.',0.0,True)
    mapping={
        'network_error':('RETRY_15_MIN','Likely transient network failure.',1.22),
        'insufficient_funds':('RETRY_24H_UPI_NUDGE','Wait before retry and suggest UPI/alternate method.',1.10),
        'bank_declined':('ALT_PAYMENT_LINK','Do not hammer the same rail; offer alternate payment method.',1.08),
        'expired_card':('UPDATE_PAYMENT_LINK','Ask customer to refresh payment credentials.',1.16),
        'auth_failed':('ASSISTED_RETRY','Provide guided retry with clear authentication instructions.',1.07),
        'checkout_abandoned':('SMART_NUDGE','Send one bounded reminder with checkout resume link.',1.18),
    }
    action,why,mult=mapping[reason]
    return action,why,mult,False


def run_batch(df: pd.DataFrame, model, seed: int=7):
    rng=random.Random(seed)
    features=['amount','failure_reason','channel','customer_segment','previous_successes','retry_count','hours_since_failure']
    probs=model.predict_proba(df[features])[:,1]
    audit=[]; recovered_amount=0.0; attempted=0; recovered_count=0
    baseline_amount=0.0; baseline_count=0
    for idx,(_,row) in enumerate(df.iterrows()):
        p=float(probs[idx])
        baseline_p=min(max(p,0.02),0.92)
        action,why,mult,stopped=policy(row,p)
        if stopped:
            effective=0.0
            outcome='stopped'
        else:
            attempted += 1
            effective=min(p*mult,0.94)
            draw=rng.random()
            baseline_won=draw < baseline_p
            won=draw < effective
            if baseline_won:
                baseline_amount += float(row['amount']); baseline_count += 1
            outcome='recovered' if won else 'not_recovered'
            if won:
                recovered_amount += float(row['amount']); recovered_count += 1
        audit.append({
            'payment_id':row['payment_id'],'amount':round(float(row['amount']),2),
            'failure_reason':row['failure_reason'],'base_probability':round(p,3),
            'action':action,'reasoning':why,'stopped':stopped,'outcome':outcome,
            'effective_probability':round(effective,3)
        })
    summary={
        'batch_size':len(df),'attempted_actions':attempted,'stopped_or_escalated':len(df)-attempted,
        'recovered_count':recovered_count,'recovered_amount':round(recovered_amount,2),
        'baseline_recovered_count_sim':baseline_count,'baseline_amount_sim':round(baseline_amount,2),
        'incremental_amount_sim':round(recovered_amount-baseline_amount,2),
        'recovery_rate':round(recovered_count/max(attempted,1),3)
    }
    (ARTIFACT_DIR/'audit_log.json').write_text(json.dumps(audit,indent=2))
    (ARTIFACT_DIR/'batch_summary.json').write_text(json.dumps(summary,indent=2))
    return summary,audit


def bootstrap():
    df=build_synthetic_dataset()
    model,metrics=train_model(df)
    batch=df.sample(80,random_state=9).reset_index(drop=True)
    summary,audit=run_batch(batch,model)
    return df,model,metrics,summary,audit
