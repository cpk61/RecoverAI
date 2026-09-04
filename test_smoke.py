from app.core import bootstrap


def test_bootstrap():
    df,model,metrics,summary,audit=bootstrap()
    assert len(df)>=500
    assert metrics['roc_auc']>0.6
    assert summary['batch_size']==80
    assert len(audit)==80
    assert all('action' in x and 'reasoning' in x for x in audit)
    assert any(x['stopped'] for x in audit)


if __name__=='__main__':
    test_bootstrap()
    print('PASS')
