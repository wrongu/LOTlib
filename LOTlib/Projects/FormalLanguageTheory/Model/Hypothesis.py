from LOTlib.Miscellaneous import logsumexp
from Levenshtein import distance
from math import log
from LOTlib.Hypotheses.Likelihoods.StochasticFunctionLikelihood import StochasticFunctionLikelihood
from LOTlib.Hypotheses.RecursiveLOTHypothesis import RecursiveLOTHypothesis
from LOTlib.Eval import RecursionDepthException
from LOTlib.Hypotheses.FactorizedDataHypothesis import FactorizedLambdaHypothesis, FactorizedDataHypothesis
from LOTlib.Hypotheses.FactorizedDataHypothesis import InnerHypothesis
from LOTlib.Examples.FormalLanguageTheory.Model.Grammar import a_grammar, eng_grammar # passed in as kwargs
from LOTlib.Miscellaneous import q


class FormalLanguageHypothesis(StochasticFunctionLikelihood, RecursiveLOTHypothesis):
    def __init__(self, grammar=None, **kwargs):
        RecursiveLOTHypothesis.__init__(self, grammar, args=[], recurse_bound=20, maxnodes=100, **kwargs)

    def __call__(self, *args):
        try:
            return RecursiveLOTHypothesis.__call__(self, *args)
        except RecursionDepthException:  # catch recursion and too big
            return None


class AnBnCnHypothesis(StochasticFunctionLikelihood, FactorizedDataHypothesis):
    """
    A particular instantiation of FactorizedDataHypothesis, with a likelihood function based on
    levenshtein distance (with small noise rate -- corresponding to -100*distance)
    """

    def __init__(self, **kwargs):
        FactorizedDataHypothesis.__init__(self, recurse_bound=5, maxnodes=125, **kwargs)

    def make_hypothesis(self, **kwargs):
        return InnerHypothesis(**kwargs)

    def compute_single_likelihood(self, datum):
        """
            Compute the likelihood with a Levenshtein noise model
        """

        assert isinstance(datum.output, dict), "Data supplied must be a dict (function outputs to counts)"

        llcounts = self.make_ll_counts(datum.input)

        lo = sum(llcounts.values())

        ll = 0.0 # We are going to compute a pseudo-likelihood, counting close strings as being close
        for k in datum.output.keys():
            ll += datum.output[k] * logsumexp([ log(llcounts[r])-log(lo) - 100.0 * distance(r, k) for r in llcounts.keys() ])
        return ll


class SimpleEnglishHypothesis(StochasticFunctionLikelihood, FactorizedLambdaHypothesis):

    def __init__(self, **kwargs):
        if 'bound' in kwargs:
            self.recurse_bound = kwargs.pop('bound')
        self.maxnodes = 125
        FactorizedLambdaHypothesis.__init__(self, recurse_bound=self.recurse_bound, maxnodes=self.maxnodes, **kwargs)

    def make_hypothesis(self, **kwargs):
        return InnerHypothesis(recurse_bound=self.recurse_bound, maxnodes=self.maxnodes, **kwargs)

    def compute_single_likelihood(self, datum):
        assert isinstance(datum.output, dict), "Data supplied must be a dict (function outputs to counts)"

        llcounts = self.make_ll_counts(datum.input)

        lo = sum(llcounts.values())

        ll = 0.0 # We are going to compute a pseudo-likelihood, counting close strings as being close
        for k in datum.output.keys():
            ll += datum.output[k] * logsumexp([ log(llcounts[r])-log(lo) - 100.0 * distance(r, k) for r in llcounts.keys() ])
        return ll


def make_hypothesis(s, **kwargs):
    """
        NOTE: grammar only has atom a, you need to add other atoms yourself
    """
    grammar = eng_grammar if s == 'SimpleEnglish' else a_grammar

    if 'terminals' in kwargs:
        terminals = kwargs.pop('terminals')
        if terminals is not None:
            for e in terminals:
                grammar.add_rule('ATOM', q(e), None, 2)

    return SimpleEnglishHypothesis(grammar=grammar, **kwargs)

