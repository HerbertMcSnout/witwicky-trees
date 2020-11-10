from __future__ import print_function
from __future__ import division

import os
import nmt.all_constants as ac
import nmt.structs as struct

'''You can add your own configuration variable to this file and select
it using `--proto variable_name`.'''

class Config(dict):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def copy(self):
        return self.__class__(**self)
    
    def adapt(self, **kwargs):
        warn = ('warn_new_option' in   self and   self['warn_new_option']) \
            or ('warn_new_option' in kwargs and kwargs['warn_new_option'])
        for k in kwargs:
            if warn and k not in self:
                raise KeyError(k)
        return self.__class__(**{k:v for k,v in list(self.items()) + list(kwargs.items())})

    def compute(self):
        computed = self.__class__()
        for k, v in self.items():
            computed[k] = v.format(**computed) if isinstance(v, str) else v
        return computed

def get_config(name, opts, overrides=None):
    '''
    Returns a dict of configurations, with default values taken from base_config.
    String options will be formatted with the values of the options defined before them,
    so "foo/{model_name}/baz" will be formatted to "foo/bar/baz" if the model name is "bar".
    The order of definition is that of base_config.
    '''
    overrides = eval(overrides or '{}', globals())
    overrides['model_name'] = name
    return opts.adapt(**overrides).compute()



base_config = Config(
    model_name = 'model_name',
    
    ### Locations of files
    save_to = 'nmt/saved_models/{model_name}',
    data_dir = 'nmt/data/{model_name}',
    log_file = '{save_to}/DEBUG.log',

    log_freq = 100,

    # Source and target languages
    # Input files should be named with these as extensions
    src_lang = 'src_lang',
    trg_lang = 'trg_lang',

    ### Model options

    # Vocabulary sizes
    src_vocab_size = 0,
    trg_vocab_size = 0,
    joint_vocab_size = 0,
    share_vocab = False,

    # Normalize word embeddings (Nguyen and Chiang, 2018)
    fix_norm = False,

    # Tie word embeddings
    tie_mode = ac.ALL_TIED,

    # Penalize position embeddings that are too big,
    # if their struct has a get_reg_penalty function
    pos_norm_penalty = 5e-2,

    # Module
    struct = struct.sequence,
    add_sinusoidal_pe_src = False,

    # Whether to learn position embeddings
    learned_pos_src = False,
    learned_pos_trg = False,

    learn_pos_scale = False,
    separate_embed_scales = False,
    
    # Layer sizes
    embed_dim = 512,
    ff_dim = 512 * 4,
    num_enc_layers = 6,
    num_enc_heads = 8,
    num_dec_layers = 6,
    num_dec_heads = 8,

    # Whether residual connections should bypass layer normalization
    # if True, layer-norm->dropout->add
    # if False, dropout->add->layer-norm (as in original paper)
    norm_in = True,

    ### Dropout/smoothing options

    dropout = 0.3,
    word_dropout = 0.1,
    label_smoothing = 0.1,

    ### Training options

    batch_sort_src = True,
    batch_size = 4096,
    weight_init_type = ac.XAVIER_NORMAL,
    normalize_loss = ac.LOSS_TOK,

    # Hyperparameters for Adam optimizer
    beta1 = 0.9,
    beta2 = 0.999,
    epsilon = 1e-8,

    # Learning rate
    warmup_steps = 24000,
    warmup_style = ac.NO_WARMUP,
    lr = 3e-4,
    lr_decay = 0, # if this is set to > 0, we'll do annealing
    start_lr = 1e-8,
    min_lr = 1e-5,
    lr_decay_patience = 3, # if no improvements for this many epochs, anneal learning rate
    early_stop_patience = 20, # if no improvements for this many epochs, stop early

    # Gradient clipping
    grad_clip = 1.0, # if no clip, just set it to some big value like 1e9
    grad_clamp = 0, # if not 0, clamp gradients to [-grad_clamp, +grad_clamp]. This happens *before* gradient clipping.
    grad_clip_pe = 0, # if 0, clip position embedding params along with all others; otherwise, clip them separately to this value

    ### Validation/stopping options

    max_epochs = 100,
    validate_freq = 1, # eval every [this many] epochs
    val_per_epoch = True, # if this true, we eval after every [validate_freq] epochs, otherwise by num of batches
    val_by_bleu = True,
    write_val_trans = False,

    # Undo BPE segmentation when validating
    restore_segments = True,

    # How many of the best models to save
    n_best = 1,

    bleu_script = 'scripts/multi-bleu.perl',

    ### Length model

    # Choices are:
    # - gnmt: https://arxiv.org/abs/1609.08144 equation 14
    # - linear: constant reward per word
    # - none
    length_model = ac.GNMT_LENGTH_MODEL,
    # For gnmt, this is the exponent; for linear, this is the strength of the reward
    length_alpha = 0.6,

    # Filter out sentences longer than this (minus one for bos/eos)
    max_src_length = 1000,
    max_trg_length = 1000,

    ### Decoding options
    beam_size = 4,

    # Warn if an adaptation introduces a new option (as it may be a typo)
    warn_new_option = True,
)



#######################################################################

second_base = base_config.adapt(
    learned_pos_src = True,
    max_src_length = 1000,
    max_epochs = 200,
    early_stop_patience = 0,
    validate_freq = 1,
    #length_model = ac.LINEAR_LENGTH_MODEL,
    #length_alpha = 0.6,
    dropout = 0.2,
    lr = 1e-4,
    restore_segments = False,
)


#######################################################################

java2doc_base = second_base.adapt(
    src_lang = 'java',
    trg_lang = 'doc',
    save_to = 'nmt/java2doc_models/{model_name}',
    joint_vocab_size = 32000,
)

java2doc_tree_base = java2doc_base.adapt(data_dir = 'nmt/data/java2doc')
java2doc_seq = java2doc_base.adapt(struct = struct.sequence, data_dir = 'nmt/data/java2doc')
java2doc_rare = java2doc_base.adapt(struct = struct.sequence)
java2doc_raw = java2doc_base.adapt(struct = struct.sequence)
java2doc17a = java2doc_tree_base.adapt(struct = struct.tree17a, grad_clamp = 100.0)
java2doc17a2 = java2doc17a.adapt(struct = struct.tree17a2)

java2doc17 = java2doc_tree_base.adapt(struct = struct.tree17c, grad_clamp = 100.0)

java2doc17a_20k = java2doc17a.adapt(data_dir = 'nmt/data/java2doc_20k')
java2doc17a2_20k = java2doc17a2.adapt(data_dir = 'nmt/data/java2doc_20k')
java2doc17_20k = java2doc17a2_20k.adapt(struct = struct.tree17c)
java2doc_seq_20k = java2doc_seq.adapt(data_dir = 'nmt/data/java2doc_20k')

java2doc_10k = java2doc17a2_20k.adapt(data_dir = 'nmt/data/java2doc_10k')
java2doc_seq_10k = java2doc_seq_20k.adapt(data_dir = 'nmt/data/java2doc_10k')

java2doc_att_sin = java2doc_base.adapt(data_dir = 'nmt/data/java2doc', struct = struct.att_sin, add_sinusoidal_pe_src = True)
java2doc_att_sin_10k = java2doc_att_sin.adapt(data_dir = 'nmt/data/java2doc_10k')
java2doc_att_sin_20k = java2doc_att_sin.adapt(data_dir = 'nmt/data/java2doc_20k')

#######################################################################

py2doc_base = second_base.adapt(
    src_lang = 'py',
    trg_lang = 'doc',
    save_to = 'nmt/py2doc_models/{model_name}',
    joint_vocab_size = 32000,
)

py2doc_tree_base = py2doc_base.adapt(data_dir = 'nmt/data/py2doc2')


py2doc_rare = py2doc_base.adapt(struct = struct.sequence)
py2doc_c = py2doc_tree_base.adapt(struct = struct.tree17c, grad_clamp = 100.0)
py2doc17a = py2doc_tree_base.adapt(struct = struct.tree17a, grad_clamp = 100.0)

#py2doc17a_20k = py2doc17a.adapt(data_dir = 'nmt/data/py2doc_20k')
#py2doc17_20k = py2doc_c.adapt(data_dir = 'nmt/data/py2doc_20k')

py2doc17 = py2doc_c

py2doc17a2 = py2doc17a.adapt(struct = struct.tree17a2)
py2doc_10k = py2doc17a2.adapt(data_dir = 'nmt/data/py2doc_10k')
py2doc_20k = py2doc17a2.adapt(data_dir = 'nmt/data/py2doc_20k')
py2doc_50k = py2doc17a2.adapt(data_dir = 'nmt/data/py2doc_50k')

py2doc_seq = py2doc_base.adapt(struct = struct.sequence, data_dir = 'nmt/data/py2doc2')
py2doc_seq_10k = py2doc_seq.adapt(data_dir = 'nmt/data/py2doc_10k')
py2doc_seq_20k = py2doc_seq.adapt(data_dir = 'nmt/data/py2doc_20k')
py2doc_seq_50k = py2doc_seq.adapt(data_dir = 'nmt/data/py2doc_50k')

py2doc_att_sin = py2doc_base.adapt(data_dir = 'nmt/data/py2doc2', struct = struct.att_sin, add_sinusoidal_pe_src = True)
py2doc_att_sin_10k = py2doc_att_sin.adapt(data_dir = 'nmt/data/py2doc_10k')
py2doc_att_sin_20k = py2doc_att_sin.adapt(data_dir = 'nmt/data/py2doc_20k')
py2doc_att_sin_50k = py2doc_att_sin.adapt(data_dir = 'nmt/data/py2doc_50k')


##########################

# Untagging doesn't really work for this dataset
en2vi_base = base_config.adapt(src_lang = 'en', trg_lang = 'vi', early_stop_patience = 0, learned_pos_src = True)
en2vi17a2_base = en2vi_base.adapt(struct = struct.tree17a2, grad_clamp = 100.0)
#en2vi_tree = en2vi_base.adapt(struct = struct.tree17c, grad_clamp = 100.0)
#en2vi17a_base = en2vi_base.adapt(struct = struct.tree17a, grad_clamp = 100.0)
#en2vi17a = en2vi17a_base.adapt(data_dir = 'nmt/data/en2vi_tree')

#en2vi17a_20k = en2vi17a.adapt(data_dir = 'nmt/data/en2vi_tree_20k')
#en2vi17_20k = en2vi_tree.adapt(data_dir = 'nmt/data/en2vi_tree_20k')

en2vi = en2vi_base # baseline
en2vi_10k = en2vi  # baseline
en2vi_20k = en2vi  # baseline
en2vi_50k = en2vi  # baseline

en2vi_att_sin = en2vi_base.adapt(data_dir = 'nmt/data/en2vi_tree', struct = struct.att_sin, add_sinusoidal_pe_src = True)
en2vi_att_sin_10k = en2vi_att_sin.adapt(data_dir = 'nmt/data/en2vi_tree_10k')
en2vi_att_sin_20k = en2vi_att_sin.adapt(data_dir = 'nmt/data/en2vi_tree_20k')
en2vi_att_sin_50k = en2vi_att_sin.adapt(data_dir = 'nmt/data/en2vi_tree_50k')

en2vi_att_sin2 = en2vi_att_sin

en2vi_seq     = en2vi.adapt(data_dir = 'nmt/data/en2vi_tree')
en2vi_seq_10k = en2vi.adapt(data_dir = 'nmt/data/en2vi_tree_10k')
en2vi_seq_20k = en2vi.adapt(data_dir = 'nmt/data/en2vi_tree_20k')
en2vi_seq_50k = en2vi.adapt(data_dir = 'nmt/data/en2vi_tree_50k')

en2vi17a2     = en2vi17a2_base.adapt(data_dir = 'nmt/data/en2vi_tree')
en2vi17a2_10k = en2vi17a2_base.adapt(data_dir = 'nmt/data/en2vi_tree_10k')
en2vi17a2_20k = en2vi17a2_base.adapt(data_dir = 'nmt/data/en2vi_tree_20k')
en2vi17a2_50k = en2vi17a2_base.adapt(data_dir = 'nmt/data/en2vi_tree_50k')


##########################
en2tu_base = base_config.adapt(src_lang = 'en', trg_lang = 'tu', early_stop_patience = 0, learned_pos_src = True)
en2tu17a2_base = en2tu_base.adapt(struct = struct.tree17a2, grad_clamp = 100.0)

en2tu = en2tu_base
en2tu_seq = en2tu.adapt(data_dir = 'nmt/data/en2tu_tree')
en2tu17a2 = en2tu17a2_base.adapt(data_dir = 'nmt/data/en2tu_tree')
en2tu_att_sin = en2tu_base.adapt(data_dir = 'nmt/data/en2tu_tree', struct = struct.att_sin, add_sinusoidal_pe_src = True)

##########################
en2ha_base = base_config.adapt(src_lang = 'en', trg_lang = 'ha', early_stop_patience = 0, learned_pos_src = True)
en2ha17a2_base = en2ha_base.adapt(struct = struct.tree17a2, grad_clamp = 100.0)

en2ha = en2ha_base
en2ha_seq = en2ha.adapt(data_dir = 'nmt/data/en2ha_tree')
en2ha17a2 = en2ha17a2_base.adapt(data_dir = 'nmt/data/en2ha_tree')
en2ha_att_sin = en2ha_base.adapt(data_dir = 'nmt/data/en2ha_tree', struct = struct.att_sin, add_sinusoidal_pe_src = True)

 
##########################

py2tree = base_config.adapt(
    max_src_length = 500,
    max_trg_length = 600,
    max_epochs = 100,
    early_stop_patience = 0,
    validate_freq = 1,
    dropout = 0.2,
    lr = 1e-4,
    restore_segments = False,
    src_lang = 'py',
    trg_lang = 'tree',
    bleu_script = 'scripts/parens.py',
)

java2tree = py2tree.adapt(
    src_lang = 'java',
)

py2tree_20k = py2tree
java2tree_20k = java2tree

##########################

#en2vi2 = en2vi_base.adapt(data_dir = 'nmt/data/en2vi', struct = struct.sequence2)
#en2vi3 = en2vi_base.adapt(data_dir = 'nmt/data/en2vi', struct = struct.trees, grad_clamp = 100.0)
#en2vi4 = en2vi_base.adapt(data_dir = 'nmt/data/en2vi', struct = struct.trees_sum, grad_clamp = 100.0)
#en2vi_forward = en2vi3.adapt(struct = struct.treesf)
#en2vi_backward = en2vi3.adapt(struct = struct.treesb)
#en2vi_dt = en2vi_tree.adapt(data_dir = 'nmt/data/en2vi_tree', num_enc_layers = 10, num_dec_layers = 10)
#en2vi14 = en2vi_base.adapt(struct = struct.tree1444f, grad_clamp = 100.0, data_dir = 'nmt/data/en2vi_tree')
#en2vi_tree = en2vi_base.adapt(struct = struct.tree17c, grad_clamp = 100.0)
#en2vi_c = en2vi_base.adapt(struct = struct.tree17c, grad_clamp = 100.0, data_dir = 'nmt/data/en2vi_tree')
#en2vi17v = en2vi_base.adapt(struct = struct.tree17v, grad_clamp = 100.0, data_dir='nmt/data/en2vi_tree')
#en2vi_ens = en2vi_base.adapt(struct = struct.tree17f, grad_clamp = 100.0, grad_clip_pe = 1.0, add_sinusoidal_pe_src = True, data_dir = 'nmt/data/en2vi_tree')
#en2vi_seq2 = en2vi_base.adapt(data_dir = 'nmt/data/en2vi_tree')
#en2vi_fix = en2vi_base.adapt(learned_pos_src = False, data_dir = 'nmt/data/en2vi_tree', struct = struct.tree17f, add_sinusoidal_pe_src = True)
#en2vi_fxs = en2vi_base.adapt(learned_pos_src = False, data_dir = 'nmt/data/en2vi_tree', struct = struct.tree17f, add_sinusoidal_pe_src = True, learn_pos_scale = True, separate_embed_scales = True)
#en2vi_abs = en2vi_base.adapt(data_dir = 'nmt/data/en2vi_tree', struct = struct.abs, add_sinusoidal_pe_src = True)
#en2vi_sin = en2vi_base.adapt(data_dir = 'nmt/data/en2vi_tree', struct = struct.tree_sin, grad_clamp = 100.0, learned_pos_src = False)
#en2vi17w = en2vi17a.adapt(num_enc_heads = 32)
#en2vi17W = en2vi17a.adapt(num_enc_heads = 16)
#en2vi_leaf_att = en2vi17a.adapt(struct = struct.leaf_att)
#en2vi17u = en2vi17a.adapt(data_dir = 'nmt/data/en2vi_untagged')
#en2vi17c = en2vi17a.adapt()#data_dir = 'nmt/data/en2vi_tree_short')
#en2vi17as = en2vi_base.adapt(data_dir = 'nmt/data/en2vi_tree_short', struct = struct.tree17a2, grad_clamp = 100.0, log_freq = 5)
#en2vi17a3 = en2vi17a.adapt(warn_new_option = False, tree_attention_heads = [()])
#en2vi_abs_sin = en2vi_base.adapt(learned_pos_src = False, struct = struct.abs_sin, data_dir = 'nmt/data/en2vi_tree')
#tree2rel = base_config.adapt(src_lang = 'tree', trg_lang = 'rel', early_stop_patience = 0, max_trg_length = 2, log_freq = 25, restore_segments = False, beam_size = 1, max_epochs = 300, bleu_script = 'scripts/one-gram.sh', lr = 1e-4)
#tree2rel2 = tree2rel.adapt(learned_pos_src = True, data_dir = 'nmt/data/tree2rel', struct = struct.tree17f, grad_clamp = 100.0, max_trg_length = 2)
#tree2rel3 = tree2rel2.adapt(struct = struct.tree17a, max_epochs = 1)
#tree2rel4 = tree2rel2.adapt(struct = struct.tree1444f)
#tree2rel_io = tree2rel2.adapt(struct = struct.tree14a, max_epochs = 1)
#tree2rel5 = tree2rel2.adapt(struct = struct.tree17f, learned_pos_src = False)
#tree2rel_bow = tree2rel2.adapt(struct = struct.bow, max_trg_length = 2)
#en2vi14a = en2vi_base.adapt(struct = struct.tree14a, grad_clamp = 100.0, data_dir = 'nmt/data/en2vi_tree')
#en2vi_att_sin = en2vi17a.adapt(struct = struct.att_sin, add_sinusoidal_pe_src = True)

#py2doc14 = py2doc_tree_base.adapt(struct = struct.tree1444f, grad_clamp = 100.0)
#py2doc17 = py2doc_tree_base.adapt(struct = struct.tree)
#py2doc17f = py2doc_tree_base.adapt(struct = struct.tree17f, grad_clamp = 100.0)
#py2doc17s = py2doc17f.adapt(add_sinusoidal_pe_src = True)
#py2doc17u = py2doc17f.adapt(data_dir = 'nmt/data/py2doc_untagged')
#py2doc17fl = py2doc17f.adapt(struct = struct.tree17fl)
#py2doc_dt = py2doc17f.adapt(num_enc_layers = 10, num_dec_layers = 10)
#py2doc17c = py2doc17a.adapt()
#py2doc_ens = py2doc_tree_base.adapt(struct = struct.tree17f, grad_clamp = 100.0, grad_clip_pe = 1.0, add_sinusoidal_pe_src = True)
#py2doc_fix = py2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = True)
#py2doc_fix2 = py2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = False)
#py2doc_fsc = py2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = True, learn_pos_scale = True, separate_embed_scales = True)
#py2doc_lsc = py2doc_tree_base.adapt(struct = struct.tree17f, add_sinusoidal_pe_src = True, learn_pos_scale = True, separate_embed_scales = True, grad_clamp = 100.0)
#py2doc_abs = py2doc_tree_base.adapt(struct = struct.abs, add_sinusoidal_pe_src = True)
#py2doc_ab = py2doc_tree_base.adapt(struct = struct.abs, add_sinusoidal_pe_src = False)
#py2doc_abs_fav = py2doc_tree_base.adapt(struct = struct.abs_fav, add_sinusoidal_pe_src = True)
#py2doc_sin = py2doc_tree_base.adapt(struct = struct.tree_sin, grad_clamp = 100.0, learned_pos_src = False)

#java2doc14 = java2doc_tree_base.adapt(struct = struct.tree1444f, grad_clamp = 100.0)
#java2doc17 = java2doc_tree_base.adapt(struct = struct.tree)
#java2doc17f = java2doc_tree_base.adapt(struct = struct.tree17f, grad_clamp = 100.0)
#java2doc17s = java2doc17f.adapt(add_sinusoidal_pe_src = True)
#java2doc17g = java2doc17f.adapt(grad_clip_pe = 1.0)
#java2doc17e = java2doc17s.adapt(grad_clip_pe = 1.0)
#java2doc17e2 = java2doc17s.adapt(grad_clip_pe = 1.0)
#java2doc17u = java2doc17f.adapt(data_dir = 'nmt/data/java2doc_untagged')
#java2doc17fl = java2doc17f.adapt(struct = struct.tree17fl)
#java2doc_dt = java2doc17f.adapt(num_enc_layers = 10, num_dec_layers = 10)
#java2doc17a3 = java2doc17a2.adapt()
#java2doc_c = java2doc_tree_base.adapt(struct = struct.tree17c, grad_clamp = 100.0)
#java2doc_ens = java2doc_tree_base.adapt(struct = struct.tree17f, grad_clamp = 100.0, grad_clip_pe = 1.0, add_sinusoidal_pe_src = True)
#java2doc_fix = java2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = True)
#java2doc_fix2 = java2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = False)
#java2doc_fsc = java2doc_tree_base.adapt(learned_pos_src = False, struct = struct.tree17f, add_sinusoidal_pe_src = True, learn_pos_scale = True, separate_embed_scales = True)
#java2doc_lsc = java2doc_tree_base.adapt(struct = struct.tree17f, add_sinusoidal_pe_src = True, learn_pos_scale = True, separate_embed_scales = True, grad_clamp = 100.0)
#java2doc17v = java2doc_tree_base.adapt(struct = struct.tree17v, grad_clamp = 100.0)
#java2doc_abs = java2doc_tree_base.adapt(struct = struct.abs, add_sinusoidal_pe_src = True)
#java2doc_ab = java2doc_tree_base.adapt(struct = struct.abs, add_sinusoidal_pe_src = False)
#java2doc_abs_fav = java2doc_tree_base.adapt(struct = struct.abs_fav, add_sinusoidal_pe_src = True)
#java2doc_sin = java2doc_tree_base.adapt(struct = struct.tree_sin, grad_clamp = 100.0, learned_pos_src = False)

#fun2com_base = base_config.adapt(
#    src_lang = 'fun',
#    trg_lang = 'com',
#    learned_pos_src = True,
#    max_epochs = 30,
#    batch_size = 3072,
#    max_trg_length = 25,
#    restore_segments = False,
#    warmup_style = ac.ORG_WARMUP,
#)
#
#fun2com_tree_base = fun2com_base.adapt(data_dir = 'nmt/data/fun2com')
#fun2com18 = fun2com_tree_base.adapt(struct = struct.tree18,)
#fun2com17 = fun2com_tree_base.adapt(struct = struct.tree,)
#fun2com17_all = fun2com_base.adapt(    struct = struct.tree,)
#fun2com172_all = fun2com_base.adapt(    data_dir = 'nmt/data/fun2com17_all',    struct = struct.tree172,)
#fun2com16 = fun2com_tree_base.adapt(    struct = struct.tree2,)
#fun2com15 = fun2com_tree_base.adapt(    struct = struct.tree15,)
#fun2com14 = fun2com_tree_base.adapt(    struct = struct.tree14,)
#fun2com142 = fun2com_tree_base.adapt(    struct = struct.tree142,)
#fun2com143 = fun2com_tree_base.adapt(    struct = struct.tree143,)
#fun2com144 = fun2com_tree_base.adapt(    struct = struct.tree144,)
#fun2com1442 = fun2com_tree_base.adapt(    struct = struct.tree1442,)
#fun2com1443 = fun2com_tree_base.adapt(    struct = struct.tree1443,)
#fun2com1444 = fun2com_tree_base.adapt(    struct = struct.tree1444,)
#fun2com1445 = fun2com_tree_base.adapt(    struct = struct.tree1445,)
#fun2com145 = fun2com_tree_base.adapt(    struct = struct.tree144,    embed_dim = 256,    ff_dim = 256 * 4,)
#fun2com146 = fun2com_tree_base.adapt(    struct = struct.tree144,    embed_dim = 128,    ff_dim = 128 * 4,)
#fun2com147 = fun2com_tree_base.adapt(    struct = struct.tree144,    embed_dim = 64,    ff_dim = 64 * 4,)
#fun2com148 = fun2com_tree_base.adapt(    struct = struct.tree144,    embed_dim = 32,    ff_dim = 32 * 4,)
#fun2com_3d = fun2com_tree_base.adapt(    struct = struct.tree14_3d,    embed_dim = 64,    ff_dim = 64 * 4,)
#fun2com_seq = fun2com_base.adapt(    struct = struct.sequence,)
#fun2com_seq2 = fun2com_base.adapt(    struct = struct.sequence2,)
#fun2com_rdr = fun2com_base.adapt(    struct = struct.sequence,)
#fun2com_src = fun2com_base.adapt(    struct = struct.sequence,)
#fun2com_sbt = fun2com_base.adapt(    max_src_length = 2000,    struct = struct.sequence,)
#fun2com_all = fun2com_base.adapt(    max_src_length = 2000,    struct = struct.sequence,)
#fun2com_rdr_all = fun2com_base.adapt(    struct = struct.sequence,)
#fun2com_seq_all = fun2com_base.adapt(    struct = struct.sequence,)
#fun2com_seq_all2 = fun2com_base.adapt(    struct = struct.sequence2,)
