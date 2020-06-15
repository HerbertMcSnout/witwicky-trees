import torch
from .struct import Struct

def normalize(t, embed_dim):
  norm = 1 if len(t.size()) == 1 else embed_dim ** 0.5
  return t * norm / t.norm()

class Tree(Struct):
  
  def __init__(self, v, l=None, r=None):
    self.l = l
    self.r = r
    self.v = v

  def __str__h(self, strs):
    if self.l:
      strs.append("(")
      strs.append(str(self.v))
      self.l.__str__h(strs)
      strs.append(")")
    else:
      strs.append(str(self.v))
    if self.r:
      self.r.__str__h(strs)
      
  def __str__(self):
    strs = []
    self.__str__h(strs)
    return " ".join(strs)

  def __repr__(self):
    return self.__str__()

  def map_(self, f):
    self.v = f(self.v)
    if self.l: self.l = self.l.map_(f)
    if self.r: self.r = self.r.map_(f)
    return self

  def map(self, f):
    v = f(self.v)
    l = self.l.map(f) if self.l else None
    r = self.r.map(f) if self.r else None
    return Tree(v, l, r)

  def flatten(self, acc=None, lefts=[]):
    if acc is None:
      acc = []
      self.flatten(acc)
      return acc
    else:
      acc.append(self.v)
      if self.l: lefts.append(self.l)
      if self.r: self.r.flatten(acc, lefts)
      elif len(lefts) > 0: lefts.pop().flatten(acc, lefts)

  def fold_up(self, f, leaf=None):
    return f(self.v, self.l.fold_up(f, leaf) if self.l else leaf, self.r.fold_up(f, leaf) if self.r else leaf)

  def fold_up_tree(self, f, leaf=None):
    l = self.l.fold_up_tree(f, leaf) if self.l else None
    r = self.r.fold_up_tree(f, leaf) if self.r else None
    lv = l.v if self.l else leaf
    rv = r.v if self.r else leaf
    v = f(self.v, lv, rv)
    return Tree(v, l, r)

  def fold_down_tree(self, f, root=None):
    l = self.l.fold_down_tree(f, f(self.v, root, True)) if self.l else None
    r = self.r.fold_down_tree(f, f(self.v, root, False)) if self.r else None
    return Tree(root, l, r)

  def zip(self, other):
    "Zips the node values of this tree with other's"
    assert (self.l is None == other.l is None) \
       and (self.r is None == other.r is None), \
       "Trying to zip two trees of different shape"
    v = self.v, other.v
    l = self.l.zip(other.l) if self.l else None
    r = self.r.zip(other.r) if self.r else None
    return Tree(v, l, r)

  def get_pos_embedding(self, embed_dim, params):
    dtype = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor
    params = [normalize(x.type(dtype), embed_dim) for x in params[:-2]] + [x.type(dtype) for x in params[-2:]]
    mu_l, mu_r, lam_leaf, lam_root, lam_leaf_l, lam_leaf_r, mu_l_scale, mu_r_scale = params
    mu_l *= mu_l_scale
    mu_r *= mu_r_scale
    step_scale = embed_dim ** 0.5

    def f_in(_, l, r): return normalize((mu_l @ l) * (mu_r @ r) * step_scale, embed_dim)

    def f_out(in_vlr, p, is_left):
      in_v, in_l, in_r = in_vlr
      in_p, out_p = p
      if is_left:
        in_r = in_r if in_r is not None else lam_leaf_r
        return in_l, normalize(torch.einsum("i,ij,i->j", out_p, mu_l, mu_r @ in_r) * step_scale, embed_dim)
      else:
        in_l = in_l if in_l is not None else lam_leaf_l
        return in_r, normalize(torch.einsum("i,i,ij->j", out_p, mu_l @ in_l, mu_r) * step_scale, embed_dim)

    def f_in_aux(v, l, r): return v, l[0], r[0]
    def f_mult(io): return normalize(io[0] * io[1] * step_scale, embed_dim)

    pe = self
    pe = pe.fold_up_tree(f_in, lam_leaf)
    pe = pe.fold_up_tree(f_in_aux, (None, None))
    pe = pe.fold_down_tree(f_out, (pe.v[0], lam_root))
    pe = pe.map(f_mult)
    #pe = pe.flatten()
    #pe = pe + [torch.zeros(embed_dim).type(dtype)] * (pad_len - len(pe))
    #return torch.stack(pe).type(dtype)
    return pe

def parse_clean(fun_str, remove_parens=True):
  # fun_str\n -> fun_str
  if fun_str[-1] == "\n": fun_str = fun_str[:-1]

  fun_str = fun_str.strip()

  # (fun_str) -> fun_str
  if fun_str[0] == "(" and fun_str[-1] == ")" and remove_parens:
    fun_str = fun_str[1:-1].strip()

  return fun_str

def parse_lc_rs_h(fun_str):
  children = []
  start = 0
  pos = 0
  while pos < len(fun_str):
    c = fun_str[pos]
    pos += 1
    if c == " " or c == "(" or c == ")":
      if start != pos - 1:
        children.append(fun_str[start:pos - 1])
      if c == "(":
        child, end = parse_lc_rs_h(fun_str[pos:])
        children.append(child)
        start = pos = pos + end
      elif c == ")": return children, pos
      else: start = pos

  if start != pos:
    children.append(fun_str[start:pos])

  return children, pos

def construct_tree(children, siblings=[]):
  return Tree(children if isinstance(children, str) else children[0],
               construct_tree(children[1], children[2:]) if len(children) > 1 and not isinstance(children, str) else None,
               construct_tree(siblings[0], siblings[1:]) if len(siblings) > 0 else None)

def parse(fun_str):
  return construct_tree(parse_lc_rs_h(parse_clean(fun_str))[0])

def get_params(config):
  embed_dim = config['embed_dim']
  mu_l = torch.Tensor(embed_dim, embed_dim)
  mu_r = torch.Tensor(embed_dim, embed_dim)
  lam_leaf   = torch.Tensor(embed_dim) # inside
  lam_root   = torch.Tensor(embed_dim) # outside
  lam_leaf_l = torch.Tensor(embed_dim) # outside
  lam_leaf_r = torch.Tensor(embed_dim) # outside
  mu_l_scale = torch.tensor([1.])
  mu_r_scale = torch.tensor([1.])
  
  torch.nn.init.orthogonal_(mu_l)
  torch.nn.init.orthogonal_(mu_r)
  torch.nn.init.normal_(lam_leaf, mean=0, std=embed_dim ** -0.5)
  torch.nn.init.normal_(lam_root, mean=0, std=embed_dim ** -0.5)
  torch.nn.init.normal_(lam_leaf_l, mean=0, std=embed_dim ** -0.5)
  torch.nn.init.normal_(lam_leaf_r, mean=0, std=embed_dim ** -0.5)
  #self.pos_embedding_linear = Parameter(torch.Tensor(max_pos_length, embed_dim))
  #torch.nn.init.normal_(self.pos_embedding_linear, mean=0, std=embed_dim ** -0.5)
  return {"mu_l":mu_l, "mu_r":mu_r, "lam_leaf":lam_leaf, "lam_root":lam_root, "lam_leaf_l":lam_leaf_l, "lam_leaf_r":lam_leaf_r,
          "mu_l_scale":mu_l_scale, "mu_r_scale":mu_r_scale}