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
from LOTlib.DataAndObjects import FunctionData
from LOTlib.Miscellaneous import logsumexp
from LOTlib.Miscellaneous import Infinity
from math import log
import sys
from mpi4py import MPI
from Simulation.utils import uniform_data
from optparse import OptionParser
from Language.Index import instance
import pstats, cProfile

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

suffix = time.strftime('_%m%d_%H%M%S', time.localtime())
fff = sys.stdout.flush

parser = OptionParser()
parser.add_option("--jump", dest="JUMP", type="int", default=2, help="")
parser.add_option("--temp", dest="TEMP", type="int", default=2, help="")
parser.add_option("--plot", dest="PLOT", type="string", default='yes', help="")
parser.add_option("--file", dest="FILE", type="string", default='', help="")
parser.add_option("--mode", dest="MODE", type="string", default='', help="")
parser.add_option("--axb", dest="AXB", type="float", default=0.3, help="")
parser.add_option("--x", dest="X", type="float", default=0.08, help="")
parser.add_option("--language", dest="LANG", type="string", default='An', help="")
parser.add_option("--finite", dest="FINITE", type="int", default=10, help="")
(options, args) = parser.parse_args()

def slice_list(input, size):
    input_size = len(input)
    slice_size = input_size / size
    remain = input_size % size
    result = []
    iterator = iter(input)
    for i in range(size):
        result.append([])
        for j in range(int(slice_size)):
            result[i].append(iterator.next())
        if remain:
            result[i].append(iterator.next())
            remain -= 1
    return result

def load_hypo(_dir, keys):
    """
    1. read raw output file

    run: serial
    """
    rec = []

    for name in listdir(_dir):
        flag = False
        for e in keys:
            if e in name: flag = True; break
        if not flag: continue

        print name; fff()
        rec.append([int(name.split('_')[1]), load(open(_dir+name, 'r'))])

    return rec

# ===========================================================================
# prase SimpleEnglish
# ===========================================================================
def most_prob(suffix):
    topn = load(open('out/SimpleEnglish/hypotheses__' + suffix))
    Z = logsumexp([h.posterior_score for h in topn])
    h_set = [h for h in topn]; h_set.sort(key=lambda x: x.posterior_score, reverse=True)
    
    for i in xrange(10):
        print h_set[i]
        print 'prob`: ', np.exp(h_set[i].posterior_score - Z)
        print Counter([h_set[i]() for _ in xrange(512)])


# ===========================================================================
# staged & skewed
# ===========================================================================
def pos_seq(rec, infos):
    """
    1. evaluate posterior probability on different data sizes

    run: serial
    """
    seq = []
    seen = set()

    for e in rec:
        for h in e[1]:
            if h in seen: continue
            seen.add(h)

    for e in infos:
        prob_dict = {}
        language = AnBn(max_length=e[1])
        eval_data = language.sample_data_as_FuncData(e[0])

        for h in seen: prob_dict[h] = h.compute_posterior(eval_data)

        seq.append(prob_dict)
        print e, 'done'; fff()

    print '='*50
    return seq


def compute_kl(current_dict, next_dict):
    current_Z = logsumexp([v for h, v in current_dict.iteritems()])
    next_Z = logsumexp([v for h, v in next_dict.iteritems()])

    kl = 0.0
    for h, v in current_dict.iteritems():
        p = np.exp(v - current_Z)
        if p == 0: continue
        kl += p * (v - next_dict[h] + next_Z - current_Z)

    return kl


def get_kl_seq():
    """
    1. read posterior sequences
    2. compute KL-divergence between adjacent distribution
    3. plot

    run: serial
    """
    print 'loading..'; fff()
    seq_set = [load(open('seq0_0825_234606')), load(open('seq1_0825_234606')), load(open('seq2_0825_234606'))]
    # seq_set = load(open('seq0_0825_195540')) + load(open('seq1_0825_195540')) + load(open('seq2_0825_195540'))
    kl_seq_set = []

    print 'compute prior..'; fff()
    # add posterior set that without observing any data
    from copy import deepcopy
    dict_0 = deepcopy(seq_set[0][0])
    for h in dict_0:
        dict_0[h] = h.compute_posterior([FunctionData(input=[], output=Counter())])

    print 'making plot..'; fff()
    for seq in seq_set:
        kl_seq = []

        # # add posterior set that without observing any data
        # from copy import deepcopy
        # dict_0 = deepcopy(seq[0])
        # for h in dict_0:
        #     dict_0[h] = h.compute_posterior([FunctionData(input=[], output=Counter())])
        seq.insert(0, dict_0)

        # compute kl
        for i in xrange(len(seq)-1):
            current_dict = seq[i]
            next_dict = seq[i+1]
            kl = compute_kl(current_dict, next_dict)
            kl_seq.append(log(kl))
            print 'KL from %i to %i: ' % (i, i+1), kl; fff()

        kl_seq_set.append(kl_seq)
        print '='*50; fff()

    staged, = plt.plot(range(12, 145, 2), kl_seq_set[0], label='staged')
    normal, = plt.plot(range(12, 145, 2), kl_seq_set[1], label='normal')
    uniform, = plt.plot(range(12, 145, 2), kl_seq_set[2], label='uniform')

    plt.legend(handles=[normal, staged, uniform])
    plt.ylabel('KL-divergence')
    plt.xlabel('data')
    plt.show()


def get_kl_seq2(jump, is_plot, file_name):
    print 'loading..'; fff()
    # TODO
    seq_set = [load(open('seq%i_' % i + file_name)) for i in xrange(3)]
    kl_seq_set = []

    # print 'prior'
    # from copy import deepcopy
    # dict_0 = deepcopy(seq_set[0][0])
    # for h in dict_0:
    #     dict_0[h] = h.compute_posterior([FunctionData(input=[], output=Counter())])

    # avg_seq_set = []
    # for i in [4, 8, 12]:
    #     for j in xrange(i-4, i):
    #         sub = [seq_set[j] for j in xrange(i-4, i)]
    #         avg_seq_set.append([(a+b+c+d)/4 for a, b, c, d in zip(*sub)])

    for seq in seq_set:
        # seq.insert(0, dict_0)
        kl_seq = []

        kl_sum = 0

        for i in xrange(len(seq)-1):
            current_dict = seq[i]
            next_dict = seq[i+1]
            kl = compute_kl(current_dict, next_dict)
            kl_sum += kl; kl_seq.append(kl_sum)
            print 'KL from %i to %i: ' % (i, i+1), kl; fff()

            f = open('tmp_out', 'a')

            print >> f, kl_sum

        kl_seq_set.append(kl_seq)
        print '='*50; fff()
        f = open('tmp_out', 'a')
        print >> f, '='*50

    # print 'avging'; fff()
    # avg_seq_set = []
    # for i in [4, 8, 12]:
    #     sub = [kl_seq_set[j] for j in xrange(i-4, i)]
    #     avg_seq_set.append([(a+b+c+d)/4 for a, b, c, d in zip(*sub)])
    #
    # for avg_seq in avg_seq_set:
    #     for i in xrange(1, len(avg_seq)):
    #         avg_seq[i] = logsumexp([avg_seq[i], avg_seq[i-1]])
    #
    # dump(kl_seq_set, open('kl_seq_set'+suffix, 'w'))
    # dump(avg_seq_set, open('avg_seq_set'+suffix, 'w'))
    #
    if is_plot == 'yes':
        staged, = plt.plot([10**e for e in np.arange(0, 2.5, 0.1)], kl_seq_set[0], label='staged')
        normal, = plt.plot([10**e for e in np.arange(0, 2.5, 0.1)], kl_seq_set[1], label='normal')
        uniform, = plt.plot([10**e for e in np.arange(0, 2.5, 0.1)], kl_seq_set[2], label='uniform')

        plt.legend(handles=[normal, staged, uniform])
        plt.ylabel('Cumulative KL-divergence')
        plt.xlabel('Size of Data')
        plt.title('SS and SF')
        plt.show()


def make_staged_seq():
    """
    1. read raw output
    2. evaluate posterior probability on different data sizes
    3. dump the sequence

    run: mpiexec -n 3
    """
    infos = [[i, 4*((i-1)/48+1)] for i in xrange(12, 145, 2)]
    # infos = [[i, 12] for i in xrange(145, 278, 2)]
    work_list = [['staged'], ['normal0'], ['normal1']]
    rec = load_hypo('out/simulations/staged/', work_list[rank])
    seq = pos_seq(rec, infos)
    dump([seq], open('seq'+str(rank)+suffix, 'w'))


def make_staged_seq2(jump, temp):
    """
    run: mpiexec -n 12
    """
    rec = load_hypo('out/simulations/staged/', ['staged', 'normal0', 'normal1'])
    seen = set()
    work_list = slice_list(range(size), 3)

    for e in rec:
        for h in e[1]:
            if h in seen: continue
            seen.add(h)

    if rank in work_list[0]:
        seq = []
        infos = [[i, min(4*((int(i)-1)/48+1), 12)] for i in [10**e for e in np.arange(0, 2.2, 0.1)]]

        for e in infos:
            prob_dict = {}
            language = AnBn(max_length=e[1]+(e[1]%2!=0))
            eval_data = language.sample_data_as_FuncData(e[0])

            for h in seen:
                h.likelihood_temperature = temp
                prob_dict[h] = h.compute_posterior(eval_data)

            seq.append(prob_dict)
            print 'rank: ', rank, e, 'done'; fff()

    elif rank in work_list[1]:
        seq = []
        infos = [[i, 12] for i in [10**e for e in np.arange(0, 2.2, 0.1)]]

        for e in infos:
            prob_dict = {}
            language = AnBn(max_length=e[1])
            eval_data = language.sample_data_as_FuncData(e[0])

            for h in seen:
                h.likelihood_temperature = temp
                prob_dict[h] = h.compute_posterior(eval_data)

            seq.append(prob_dict)
            print 'rank: ', rank, e, 'done'; fff()

    else:
        seq = []
        infos = [[i, 12] for i in [10**e for e in np.arange(0, 2.2, 0.1)]]

        for e in infos:
            prob_dict = {}
            eval_data = uniform_data(e[0], e[1])

            for h in seen:
                h.likelihood_temperature = temp
                prob_dict[h] = h.compute_posterior(eval_data)

            seq.append(prob_dict)
            print 'rank: ', rank, e, 'done'; fff()

    # TODO no need ?
    from copy import deepcopy
    dict_0 = deepcopy(seq[0])
    for h in dict_0:
        dict_0[h] = h.compute_posterior([FunctionData(input=[], output=Counter())])
    seq.insert(0, dict_0)
    dump(seq, open('seq'+str(rank)+suffix, 'w'))


def test_sto():
    """
    objective: test if our posterior distribution is stable for each time of estimation

    run: mpiexec -n 12
    """
    rec = load_hypo('out/simulations/staged/', ['staged', 'normal0', 'normal1'])
    # rec = load_hypo('out/simulations/staged/', ['staged'])

    seen = set()
    for e in rec:
        for h in e[1]:
            if h in seen: continue
            seen.add(h)
    print rank, 'hypo len: ', len(seen); fff()

    seq = []
    inner_kl_seq = []
    infos = [[i, 4*((i-1)/48+1)] for i in xrange(12, 145, 2)]

    for e in infos:
        prob_dict = {}
        language = AnBn(max_length=e[1])
        eval_data = language.sample_data_as_FuncData(e[0])

        for h in seen:prob_dict[h] = h.compute_posterior(eval_data)

        seq.append(prob_dict)
        if len(seq) > 1: inner_kl_seq.append(compute_kl(seq[-2], seq[-1]))
        print 'rank: ', rank, e, 'done'; fff()

    dump(seq, open('seq_'+str(rank)+suffix,'w'))
    dump(inner_kl_seq, open('inner_kl_seq_'+str(rank)+suffix, 'w'))

    if rank != 0:
        comm.send(seq, dest=0)
        print rank, 'send'; fff()
        sys.exit(0)
    else:
        seq_set = [seq]
        for i_s in xrange(size - 1):
            seq_set.append(comm.recv(source=i_s+1))
            print rank, 'recv:', i_s; fff()

        cross_kl_seq = []
        for i_s in xrange(len(seq_set[0])):
            tmp = []

            for i_ss in xrange(len(seq_set)-1):
                current_dict = seq_set[i_ss][i_s]
                next_dict = seq[i_ss+1][i_s]
                tmp.append(compute_kl(current_dict, next_dict))
                print 'row %i column %i done' % (i_ss, i_s); fff()

            cross_kl_seq.append(tmp)

        dump(cross_kl_seq, open('cross_kl_seq_'+str(rank)+suffix, 'w'))
        for e in cross_kl_seq:
            print e; fff()


def test_hypo_stat():
    """
    objective: test how does those high prob hypotheses look like

    run: mpiexec -n 12
    """

    seq = load(open('seq_'+str(rank)+''))

    cnt = 0
    for e in seq:
        Z = logsumexp([p for h, p in e.iteritems()])
        e_list = [[h, p] for h, p in e.iteritems()]; e_list.sort(key=lambda x:x[1], reverse=True)
        f = open('hypo_stat_'+str(rank)+suffix, 'a')

        print >> f, '='*40
        for iii in xrange(4):
            print >> f, 'rank: %i' % rank, 'prob', np.exp(e_list[iii][1] - Z)
            print >> f, Counter([e_list[iii][0]() for _ in xrange(512)])
            print >> f, str(e_list[iii][0])

        print cnt, 'done'; cnt += 1
        f.close()


# ===========================================================================
# nonadjacent
# ===========================================================================
def make_pos(jump, temp):
    """
    1. read raw output
    2. compute precision & recall on nonadjacent and adjacent contents
    3. evaluate posterior probability on different data sizes
    4. dump the sequence

    run: mpiexec -n 4
    """

    print 'loading..'; fff()
    rec = load_hypo('out/simulations/nonadjacent/', ['0'])

    print 'estimating pr'; fff()
    pr_dict = {}
    _set = set()
    cnt_tmp = {}
    for e in rec:
        for h in e[1]:
            if h in _set: continue
            cnt = Counter([h() for _ in xrange(256)])
            # cnt = Counter([h() for _ in xrange(10)])
            cnt_tmp[h] = cnt
            base = sum(cnt.values())
            num = 0
            for k, v in cnt.iteritems():
                if k is None or len(k) < 2: continue
                if k[0] == 'a' and k[-1] == 'b': num += v
            pr_dict[h] = float(num) / base
            _set.add(h)

    work_list = range(2, 24, jump)
    space_seq = []
    for i in work_list:
        language = LongDependency(max_length=i)

        eval_data = {}
        for e in language.str_sets:
            eval_data[e] = 144.0 / len(language.str_sets)
        eval_data = [FunctionData(input=[], output=eval_data)]

        prob_dict = {}
        ada_dict = {}
        test_list = []

        for h in _set:
            h.likelihood_temperature = temp
            prob_dict[h] = h.compute_posterior(eval_data)
            p, r = language.estimate_precision_and_recall(h, cnt_tmp[h])
            ada_dict[h] = 2*p*r/(p+r) if p+r != 0 else 0

            test_list.append([h.posterior_score, ada_dict[h], pr_dict[h], cnt_tmp[h], str(h)])

        Z = logsumexp([h.posterior_score for h in _set])
        test_list.sort(key=lambda x:x[0], reverse=True)

        weighted_x = 0
        weighted_axb = 0
        for e in test_list:
            weighted_x += np.exp(e[0] - Z) * e[1]
            weighted_axb += np.exp(e[0] - Z) * e[2]
        f = open('non_w'+suffix, 'a')
        print >> f, weighted_x, weighted_axb
        f.close()
        # print rank, i, '='*50
        # for i_t in xrange(3):
        #     print 'prob: ', np.exp(test_list[i_t][0] - Z), 'x_f-score',  test_list[i_t][1], 'axb_f-score',  test_list[i_t][2]
        #     print test_list[i_t][3]
            # print test_list[i_t][5].compute_posterior(eval_data)
            # print language.estimate_precision_and_recall(test_list[i_t][5], cnt_tmp[test_list[i_t][5]])
        # fff()
        # dump(test_list, open('test_list_'+str(rank)+'_'+str(i)+suffix, 'w'))

        # space_seq.append([prob_dict, ada_dict])
        print 'rank', rank, i, 'done'; fff()

    dump([space_seq, pr_dict], open('non_seq'+str(rank)+suffix, 'w'))


def make_pos2(jump, temp):
    """
    1. read raw output
    2. compute precision & recall on nonadjacent and adjacent contents
    3. evaluate posterior probability on different data sizes
    4. dump the sequence

    run: mpiexec -n 4
    """

    print 'loading..'; fff()
    rec = load_hypo('out/simulations/nonadjacent/', ['0'])

    print 'estimating pr'; fff()
    pr_dict = {}
    _set = set()
    cnt_tmp = {}
    for e in rec:
        for h in e[1]:
            if h in _set: continue
            cnt = Counter([h() for _ in xrange(1024)])
            cnt_tmp[h] = cnt
            base = sum(cnt.values())
            num = 0
            for k, v in cnt.iteritems():
                if k is None or len(k) < 2: continue
                if k[0] + k[-1] in ['ab', 'cd', 'ef']: num += v
            pr_dict[h] = float(num) / base
            _set.add(h)

    work_list = range(2, 17, jump)
    for i in work_list:
        language = LongDependency(max_length=i)

        eval_data = {}
        for e in language.str_sets:
            eval_data[e] = 144.0 / len(language.str_sets)
        eval_data = [FunctionData(input=[], output=eval_data)]

        score = np.zeros(len(_set), dtype=np.float64)
        prec = np.zeros(len(_set), dtype=np.float64)

        # prob_dict = {}
        # test_list = []

        for ind, h in enumerate(_set):
            h.likelihood_temperature = temp
            score[ind] = h.compute_posterior(eval_data)
            prec[ind] = pr_dict[h]
            # prob_dict[h] = h.compute_posterior(eval_data)
            # test_list.append([h.posterior_score, pr_dict[h], cnt_tmp[h], str(h), h])

        # test_list.sort(key=lambda x: x[0], reverse=True)
        # Z = logsumexp([h.posterior_score for h in _set])
        #
        # weighted_axb = sum([np.exp(e[0] - Z) * e[1] for e in test_list])
        # print i, weighted_axb
        # for i_t in xrange(3):
        #     print 'prob: ', np.exp(test_list[i_t][0] - Z), 'axb_f-score',  test_list[i_t][1]
        #     print test_list[i_t][2]
        #     # print test_list[i_t][4].compute_posterior(eval_data)
        #     # print language.estimate_precision_and_recall(test_list[i_t][5], cnt_tmp[test_list[i_t][5]])
        # print '='*50
        # fff()

        #
        # f = open('non_w'+suffix, 'a')
        # print >> f, Z, weighted_axb
        # print
        # f.close()
        #
        # print 'size: %i' % i, Z, weighted_axb; fff()

        if rank != 0:
            comm.send(score, dest=0)
            comm.send(prec, dest=0)
        else:
            for r in xrange(size - 1):
                score += comm.recv(source=r+1)
                prec += comm.recv(source=r+1)
            score /= size
            prec /= size
            Z = logsumexp(score)

            weighted_axb = np.sum(np.exp(score-Z) * prec)

            f = open('non_w'+suffix, 'a')
            print >> f, Z, weighted_axb
            print i, Z, weighted_axb; fff()
            f.close()
        # dump([space_seq, pr_dict], open('non_seq'+str(rank)+suffix, 'w'))


def dis_pos(jump, is_plot, file_name, axb_bound, x_bound):
    """
    1. read posterior sequence
    2. set bound for axb and x hypotheses
    3. plot

    run: serial
    """
    # space_seq, pr_dict = load(open('non_seq%i_' % i + file_name))
    print 'loading..'; fff()
    _set = [load(open('non_seq%i_' % i + file_name)) for i in xrange(4)]

    print 'avging..'; fff()
    avg_space_seq, avg_pr_dict = _set.pop(0)
    for space_seq, pr_dict in _set:
        for i in xrange(len(space_seq)):
            prob_dict, ada_dict = space_seq[i]
            avg_prob_dict, avg_ada_dict = avg_space_seq[i]
            for h in prob_dict:
                avg_prob_dict[h] = logsumexp([avg_prob_dict[h], prob_dict[h]])
                avg_ada_dict[h] += ada_dict[h]
        for h in pr_dict:
            avg_pr_dict[h] += pr_dict[h]

    for prob_dict, ada_dict in avg_space_seq:
        for h in prob_dict:
            prob_dict[h] -= 4
            ada_dict[h] /= 4
    for h in avg_pr_dict:
        avg_pr_dict[h] /= 4

    for axb_bound in np.arange(0.1, 1, 0.1):
        for x_bound in np.arange(0.1, 1, 0.1):
            seq = []
            seq1 = []
            seq2 = []
            for seen in avg_space_seq:
                Z = logsumexp([p for h, p in seen[0].iteritems()])

                axb_prob = -Infinity
                x_prob = -Infinity

                for h, v in seen[0].iteritems():
                    if avg_pr_dict[h] > axb_bound: axb_prob = logsumexp([axb_prob, v])
                    if seen[1][h] > x_bound: x_prob = logsumexp([x_prob, v])

                seq.append(np.exp(axb_prob - Z))
                seq1.append(np.exp(x_prob - Z))
                seq2.append(np.exp(axb_prob - Z) - np.exp(x_prob - Z))
                print 'done'; fff()

            flag = True
            for i in xrange(len(seq2) - 1):
                if seq2[i] - seq2[i+1] > 1e-4:
                    flag = False; break
            if not flag: continue

            print axb_bound, x_bound, '='*50
            print 'axb_prob: ', seq
            print 'x_prob: ', seq1
            print 'difference_prob: ', seq2; fff()
            dump([seq, seq1, seq2], open('nonadjacent_%.2f_%.2f' % (axb_bound, x_bound)+suffix, 'w'))

            if is_plot == 'yes':
                f, axarr = plt.subplots(1, 3)
                axarr[0].plot(range(2, 65, jump), seq)
                axarr[1].plot(range(2, 65, jump), seq1)
                axarr[2].plot(range(2, 65, jump), seq2)

                # plt.legend(handles=[x])
                plt.ylabel('posterior')
                plt.xlabel('poo_size')
                plt.show()


def test_lis_disp(names):
    ll = [load(open(name)) for name in names]
    for li in ll:
        print '='*50
        Z = logsumexp([h[0] for h in li])
        for i in xrange(3):
                print 'p ', np.exp(li[i][0] -Z), 'x_f-score ', li[i][1], 'axb_f-score', li[i][2]
                print li[i][4]

# ===========================================================================
# parse & plot
# ===========================================================================
def parse_plot(lang_name, finite, is_plot):
    """
        run: mpi supported
    """
    _dir = 'out/final/'
    global size
    global rank

    print 'loading..'; fff()
    topn = set()
    for file_name in listdir(_dir):
        if lang_name in file_name:
            _set = load(open(_dir+file_name))
            topn.update([h for h in _set])

    language = instance(lang_name, finite)

    print 'getting p&r..'; fff()
    prf_dict = {}
    pr_data = language.sample_data_as_FuncData(1024)
    for h in topn:
        p, r = language.estimate_precision_and_recall(h, pr_data)
        prf_dict[h] = [p, r, 0 if p+r == 0 else 2*p*r/(p+r)]

    if rank == 0:
        dump(prf_dict, open(lang_name+'_prf_dict'+suffix, 'w'))

    print rank, 'getting posterior'; fff()
    work_list = slice_list(np.arange(0, 30, 1), size)
    seq = []
    for s in work_list[rank]:
        eval_data = language.sample_data_as_FuncData(s)
        for h in topn:
            h.likelihood_temperature = 100
            h.compute_posterior(eval_data)

        Z = logsumexp([h.posterior_score for h in topn])
        wfs = sum([prf_dict[h][2]*np.exp(h.posterior_score - Z) for h in topn])
        seq.append([s, wfs])
        print 'size: %.1f' % s, 'weighted F-score: %.2f' % wfs; fff()

        #debug
        _list = [h for h in topn]; _list.sort(key=lambda x: x.posterior_score, reverse=True)
        for i in xrange(3):
            print 'prob: ', np.exp(_list[i].posterior_score - Z), 'p,r: ', prf_dict[_list[i]][:2],
            print Counter([_list[i]() for _ in xrange(256)])
            print _list[i]
        print '='*50; fff()

    if rank == 0:
        for i in xrange(1, size):
            seq += comm.recv(source=i)
    else:
        comm.send(seq, dest=0)
        sys.exit(0)

    seq.sort(key=lambda x: x[0])
    dump(seq, open(lang_name+'_seq'+suffix, 'w'))

    if is_plot == 'yes':
        x, y = zip(*seq)
        plt.plot(x, y)

        plt.ylabel('Weighted F-score')
        plt.xlabel('Size of Data')
        plt.title(lang_name)
        plt.show()


def only_plot(lang_name, suffix):
    seq = load(open(lang_name+'_seq'+suffix))
    x, y = zip(*seq)
    plt.plot(x, y)

    plt.ylabel('Weighted F-score')
    plt.xlabel('Size of Data')
    plt.title(lang_name)
    plt.show()

if __name__ == '__main__':

    if options.MODE == 'staged_mk':
        make_staged_seq2(jump=options.JUMP, temp=options.TEMP)
    elif options.MODE == 'staged_plt':
        get_kl_seq2(jump=options.JUMP, is_plot=options.PLOT, file_name=options.FILE)
    elif options.MODE == 'nonadjacent_mk':
        make_pos2(jump=options.JUMP, temp=options.TEMP)
    elif options.MODE == 'nonadjacent_plt':
        dis_pos(jump=options.JUMP, is_plot=options.PLOT, file_name=options.FILE, axb_bound=options.AXB, x_bound=options.X)
    elif options.MODE == 'parse_simple':
        most_prob(options.FILE)
    elif options.MODE == 'parse_plot':
        parse_plot(options.LANG, options.FINITE, is_plot=options.PLOT)
    elif options.MODE == 'only_plot':
        only_plot(options.LANG, options.FILE)

    # seq = [[2  ,0.167012421	], [4  ,0.404128998	], [6  ,0.408503541], [8  ,0.346094762], [10 ,0.43615293], [12 ,0.995324843], [14 ,0.987169], [16 ,0.979347514], [18 ,0.983990461], [20 ,0.988215573	], [22 ,0.970604139	], [24 ,1]]
    # x, y = zip(*seq)
    # plt.plot(x, y)
    #
    # plt.ylabel('Weighted F-score')
    # plt.xlabel('Size of Data')
    # plt.title('Nonadjacent Dependency')
    # plt.show()

    # test_hypo_stat()
    #
    # cProfile.runctx("test_sto()", globals(), locals(), "Profile.prof")
    # s = pstats.Stats("Profile.prof")
    # s.strip_dirs().sort_stats("time").print_stats()

    # avg_seq_set = load(open('avg_seq_set_0829_022210'))
    # for avg_seq in avg_seq_set:
    #     for i in xrange(1, len(avg_seq)):
    #         avg_seq[i] = logsumexp([avg_seq[i], avg_seq[i-1]])
    #
    # staged, = plt.plot(range(12, 145, 30), avg_seq_set[0], label='staged')
    # normal, = plt.plot(range(12, 145, 30), avg_seq_set[1], label='normal')
    # uniform, = plt.plot(range(12, 145, 30), avg_seq_set[2], label='uniform')
    #
    # plt.legend(handles=[normal, staged, uniform])
    # plt.ylabel('KL-divergence')
    # plt.xlabel('data')
    # plt.show()
