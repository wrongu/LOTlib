"""
Find N best number game hypotheses.

"""
from LOTlib.FiniteBestSet import FiniteBestSet
from LOTlib.Inference.MetropolisHastings import MHSampler
from LOTlib.Inference.PriorSample import prior_sample
from Model import *

# Global parameters for inference
domain = 100
alpha = 0.9
num_iters = 10000
N = 10
h0 = make_h0(grammar=grammar, alpha=alpha)
demo_data = [1,1,1,1,1,1,2,2,2,2,2,2,2,7,7,7,7,7,8,8,8,8,8,8,8,8,9,9,9,9,9,9,9,9]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
prior_sampler = prior_sample(h0, demo_data, num_iters)
mh_sampler = MHSampler(h0, demo_data, num_iters)

hypos = [h for h in prior_sampler]
for h in hypos:
    h.compute_posterior([8])

hypos = sorted(set(hypos), key=lambda x: x.posterior_score)
for h in hypos[-10:]:
    print str(h), h.posterior_score, h.likelihood, h.prior
# hypotheses = FiniteBestSet(generator=prior_sampler, N=N, key="posterior_score")
# for h in hypotheses:
#     print str(h), h.posterior_score
