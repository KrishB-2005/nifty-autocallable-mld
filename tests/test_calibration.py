import numpy as np
import pytest

from mld.bs import black
from mld.calibration import calibrate


@pytest.fixture(scope="module")
def cal():
    return calibrate()


def test_market_forwards_are_reproduced(cal):
    m = cal.market
    for r in cal.forwards.itertuples():
        assert m.forward(r.T) == pytest.approx(r.F, rel=1e-10)


def test_implied_vols_reprice_the_quotes(cal):
    iv = cal.ivs
    D = cal.curve.df(iv["T"].values)
    model = black(iv.F.values, iv.K.values, iv["T"].values, iv.iv.values, D, "call")
    puts = iv.kind.values == "put"
    model = np.where(puts, model - D * (iv.F.values - iv.K.values), model)
    np.testing.assert_allclose(model, iv.price.values, rtol=1e-6)


def test_term_structure_has_no_calendar_arbitrage(cal):
    v = cal.market.vol
    assert np.all(np.diff(v.vols ** 2 * v.tenors) > 0)
    assert 0.08 < float(v.vol(3.0)) < 0.30


def test_smile_has_put_skew(cal):
    assert (cal.smiles["skew"] < 0).all()
