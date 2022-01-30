import collections

class Tree:
  def __init__(self, left=None, right=None):
    self.left = left
    self.right = right

class Huffman:
  def __init__(self, string, ignore=None):
    ignore = ignore or []
    self.freqs = self.count_frequencies(string, ignore)
    self._tree = self.construct_frequency_tree()
    self.code = self.generate_huffman_code(self._tree[0][0], [])

  def count_frequencies(self, string, ignore):
    freq = collections.defaultdict(int)
    for char in string:
      if char in ignore:
        continue
      freq[char] += 1
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)

  def construct_frequency_tree(self):
    nodes = self.freqs
    while len(nodes) > 1:
      key1, val1 = nodes[-1]
      key2, val2 = nodes[-2]
      node = Tree(key1, key2)
      nodes = nodes[:-2]
      nodes.append((node, val1 + val2))
      nodes = sorted(nodes, key=lambda x: x[1], reverse=True)
    return nodes

  def generate_huffman_code(self, node, binary, is_left_node=True):
    if isinstance(node, str) or isinstance(node, int):
      return {node: binary}
    d = {}
    d.update(self.generate_huffman_code(node.left, binary + [0], True))
    d.update(self.generate_huffman_code(node.right, binary + [1], False))
    return d

