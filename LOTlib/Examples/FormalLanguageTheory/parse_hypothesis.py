from pickle import load, dump
from collections import Counter

from LOTlib.Evaluation.Eval import register_primitive
from LOTlib.Miscellaneous import flatten2str
import numpy as np
from LOTlib.Examples.FormalLanguageTheory.Language.SimpleEnglish import SimpleEnglish
register_primitive(flatten2str)
import matplotlib.pyplot as plt
from os import listdir
from LOTlib.Examples.FormalLanguageTheory.Language.AnBn import AnBn
from LOTlib.Examples.FormalLanguageTheory.Language.LongDependency import LongDependency
import time
from LOTlib.Miscellaneous import logsumexp
from LOTlib.Miscellaneous import Infinity

def load_hypo(_dir, keys):
    rec = []

    for name in listdir(_dir):
        try:
            for e in keys:
                if e not in name: raise Exception
        except: continue

        print name
        rec.append([int(name.split('_')[1]), load(open(_dir+name))])

    return rec


def get_wfs_seq(rec, eval_data, pr_data, estimate_precision_and_recall):
    pr_dict = {}
    for _set in rec:
        for h in _set[1]:
            h.compute_posterior(eval_data)
            precision, recall = estimate_precision_and_recall(h, pr_data)
            pr_dict[h] = [precision, recall]

    space = set()
    seq = []
    infos = [[12*(i+1), 4*(1+i/4)] for i in xrange(12)]

    for e in rec:
        space.update(e[1])

    for i in xrange(12):
        seq.append(probe(space, pr_dict, infos[i])[1])

    return seq


def probe(best_hypotheses, pr_dict, data_info):
    eval_data = language.sample_data_as_FuncData(data_info[0], max_length=data_info[1])
    for h in best_hypotheses:
        h.compute_posterior(eval_data)

    Z = logsumexp([h.posterior_score for h in best_hypotheses])

    score_sum = 0
    best = 0
    s = None
    rec = []

    for h in best_hypotheses:
        precision, recall = pr_dict[h]
        base = precision + recall

        if base != 0:
            p = np.exp(h.posterior_score - Z)
            weighted_score = p * (precision * recall / base)
            if weighted_score > best:
                best = weighted_score
                s = str(h)
            score_sum += weighted_score

            if p > 1e-2:
                rec.append([p, 2 * precision * recall / base])

    score_sum *= 2
    rec.sort(key=lambda x: x[0], reverse=True)
    return Z, score_sum, best*2, s, rec


def get_axb_prob(rec, B, C):
    language = LongDependency(B=B, C=C)
    eval_data = language.sample_data_as_FuncData(144, max_length=5)
    pr_data = language.sample_data_as_FuncData(1024, max_length=5)

    precisions = {}
    seen = set()
    for _set in rec:
        for h in _set[1]:
            if h in seen: continue
            h.compute_posterior(eval_data)
            # precisions[h] = language.estimate_precision_and_recall(h, pr_data)[0]
            seen.add(h)

    Z = logsumexp([h.posterior_score for h in seen])

    _set = []
    for h in seen:
        _set.append([str(h), np.exp(h.posterior_score - Z), Counter([h() for _ in xrange(256)])])
    _set.sort(key=lambda x: x[1], reverse=True)

    for i in xrange(5):
        print _set[i][0]
        print _set[i][1]
        print _set[i][2]
    print '*'*20
    # axb_prob = -Infinity
    # for h in seen:
    #     if precisions[h] > 0.6: axb_prob = logsumexp([axb_prob, h.posterior_score])
    #
    # print np.exp(axb_prob - Z)



# language = AnBn()
# eval_data = language.sample_data_as_FuncData(144, max_length=12)
# pr_data = language.sample_data_as_FuncData(1024, max_length=12)
#
# rec = load_hypo('out/simulations/staged/inf/', ['staged'])
# seq = get_wfs_seq(rec, eval_data, pr_data, language.estimate_precision_and_recall)
# staged, = plt.plot(range(1, 13), seq, label='staged')
#
# rec = load_hypo('out/simulations/staged/inf/', ['normal'])
# seq1 = get_wfs_seq(rec, eval_data, pr_data, language.estimate_precision_and_recall)
# normal, = plt.plot(range(1, 13), seq1, label='normal')
#
# suffix = time.strftime('_%m%d_%H%M%S', time.localtime())
# dump([seq, seq1], open('seq'+suffix, 'w'))
# plt.legend(handles=[normal, staged])
# plt.ylabel('weighted F-score')
# plt.xlabel('blocks')
# plt.show()

rec = load_hypo('out/simulations/nonadjacent/', ['0'])
get_axb_prob(rec, 'b', ['c', 'd'])

# get_axb_prob(rec, 'c', ['c', 'd'])
# get_axb_prob(rec, 'd', ['c', 'd'])
#
get_axb_prob(rec, 'b', ['c', 'd', 'e'])
# get_axb_prob(rec, 'c', ['c', 'd', 'f'])
# get_axb_prob(rec, 'd', ['c', 'd', 'e'])
# get_axb_prob(rec, 'e', ['c', 'd', 'f'])
#
get_axb_prob(rec, 'b', ['c', 'd', 'e', 'f'])




# h_set = []
#
# h_set.append(load(open('hypo_1__0819_204954')))
# h_set.append(load(open('hypo_0__0819_204954')))
# h_set.append(load(open('hypo_2__0819_204954')))
# h_set.append(load(open('hypo_3__0819_204954')))
# h_set.append(load(open('hypo_4__0819_204954')))
#
# h_set = load(open('hypotheses__0819_183013'))
#
# for e in h_set:
#     for h in e:
#         print Counter([h() for _ in xrange(1024)])
#         print str(h)

# h_m = None
# for h in h_set:
#     if 'cons_(\'a\', cons_(\'a\', ( \'\' if empty_(cdr_(recurse_())) else cons_(\'b\', cons_(\'b\', \'\')) ))) if flip_() else' in str(h):
#         h_m = h
#         print Counter([h() for _ in xrange(1024)])
#         print str(h)
#
# DATA_RANGE = np.arange(10, 400, 21)
# language = SimpleEnglish()
#
#
# for size in DATA_RANGE:
#     evaluation_data = language.sample_data_as_FuncData(size, max_length=5)
#     h_m.compute_posterior(evaluation_data)
#     print size, h_m.posterior_score / size


# def get_rec(name):
#     f = open(name)
#     rec = []
#     iter = 0
#     for line in f:
#         if iter % 2 == 0:
#             rec.append(float(line.split()[3]))
#         iter += 1
#     return rec


# rec = get_rec('out/simulations/staged/normal_out_4__0820_002642')
# normal, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='normal4')

# rec = get_rec('out/simulations/staged/normal_out_3__0820_002642')
# normal1, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='normal3')
#
# rec = get_rec('out/simulations/staged/normal_out_2__0820_002642')
# normal2, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='normal2')
#
# rec = get_rec('out/simulations/staged/normal_out_1__0820_002642')
# normal3, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='normal1')


# rec = get_rec('out/simulations/staged/staged_out_4__0820_002642')
# staged, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='staged4')
#
# rec = get_rec('out/simulations/staged/staged_out_3__0820_002642')
# staged1, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='staged3')
#
# rec = get_rec('out/simulations/staged/staged_out_2__0820_002642')
# staged2, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='staged2')
#
# rec = get_rec('out/simulations/staged/staged_out_1__0820_002642')
# staged3, = plt.plot([i*200 for i in xrange(len(rec))], rec, label='staged1')

# plt.legend(handles=[normal, staged1])
# plt.ylabel('weighted F-score')
# plt.xlabel('MCMC steps')
# plt.show()