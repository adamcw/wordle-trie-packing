class Trie:
  def __init__(self, words, word_func=None, variable_length=False):
    self.trie = {}
    for i, word in enumerate(words):
      node = self.trie
      if word_func:
        word = word_func(word)
      for letter in word:
        if letter not in node:
          node[letter] = {}
        node = node[letter]
      if variable_length:
        node['END'] = {}

  def count_children(self):
    children = []
    self._count_children(self.trie, children)
    return children

  def leaves_at_depth(self, target_depth):
    return self._leaves_at_depth(self.trie, target_depth)

  def _leaves_at_depth(self, trie, target_depth, depth=0):
    if depth == target_depth:
      return trie.keys()
    keys = []
    for v in trie.values():
      keys += self._leaves_at_depth(v, target_depth, depth+1)
    return keys

  def _count_children(self, trie, children):
    children.append(len(trie))
    for k, v in trie.items():
      self._count_children(v, children)

  def _max_children(self, trie):
    max_len = 0
    for k, v in trie.items():
      v_len = len(v)
      max_len = max(max_len, v_len)
      max_len = max(max_len, self._max_children(v))
    return max_len
