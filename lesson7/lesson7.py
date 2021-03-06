from bitstring import BitArray
import collections
import functools
import itertools
import json
import math
import time

class Tree:
  def __init__(self, left=None, right=None):
    self.left = left
    self.right = right

def construct_frequency_tree(freqs):
  nodes = freqs
  while len(nodes) > 1:
    key1, val1 = nodes[-1]
    key2, val2 = nodes[-2]
    node = Tree(key1, key2)
    nodes = nodes[:-2]
    nodes.append((node, val1 + val2))
    nodes = sorted(nodes, key=lambda x: x[1], reverse=True)
  return nodes

def generate_huffman_code(node, binary, is_left_node=True):
  if isinstance(node, str) or isinstance(node, int):
    return {node: binary}
  d = {}
  d.update(generate_huffman_code(node.left, binary + [0], True))
  d.update(generate_huffman_code(node.right, binary + [1], False))
  return d

def count_frequencies(string):
  freq = collections.defaultdict(int)
  for char in string:
    freq[char] += 1
  return sorted(freq.items(), key=lambda x: x[1], reverse=True)

def max_len_table(tables):
  return max([len(huff) for huff in tables])

def bits_needed_to_represent(num):
  mask = 0b1 << 32
  for i in range(32):
    if (((num & mask) >> 31 - i)):
      return 32 - i + 1;
    mask >>= 1
  return 0

def leaves_at_depth(trie, target_level, level=0):
  if level == target_level:
    return trie.keys()
  keys = []
  for v in trie.values():
    keys += leaves_at_depth(v, target_level, level+1)
  return keys

def count_children_trie(trie, children):
  children.append(len(trie.keys()))
  for k, v in trie.items():
    count_children_trie(v, children)

def max_children_trie(trie):
  max_len = 0
  for k, v in trie.items():
    v_len = len(v.keys())
    max_len = max(max_len, v_len)
    max_len = max(max_len, max_children_trie(v))
  return max_len

def convert_trie_to_bits(trie, bit_trie, tables, depth=0, smart=False):
  for k, v in trie.items():
    if not smart or v.keys():
      bit_trie.append(tables[-1][len(v.keys())])
    bit_trie.append(tables[depth][k])
    convert_trie_to_bits(v, bit_trie, tables, depth+1, smart=smart)

class BitStream:
  def __init__(self, bit_array, char_map=None):
    self.bits = bit_array
    self.bin = self.bits.bin
    self.i = 0
    self.char_map = char_map

  def write(self, key, num_bits):
    bits = []
    val = self.char_map[key] if isinstance(key, str) else key
    mask = 0b1 << num_bits - 1
    for i in range(1, num_bits + 1):
      bits.append((val & mask) >> num_bits - i)
      mask >>= 1
    self.bits.append(bits)

  def append(self, data):
    self.bits.append(data)

  def read(self, num_bits):
    bits = self.bin[self.i:self.i+num_bits]
    self.i += num_bits
    return bits

  def read_int(self, num_bits):
    return int(self.read(num_bits), 2)

  def read_varint(self, table):
    buf = ''
    i = 0
    while True:
      buf += str(self.read(1))
      if buf in table.keys():
        return table[buf]
      i += 1
      #if i > max(map(len, table.keys())):
      #  print(i, buf, table.keys())
      #  sys.exit()

  def __len__(self):
    return len(self.bits)

def read_payload_trie(bits, symbols, tables, depth=0, prefix=''):
  num_children = 0
  if depth < len(tables) - 2:
    num_children = bits.read_varint(tables[-1])
  symbol = bits.read_varint(tables[depth])
  char = symbols[symbol]
  if depth == len(tables) - 2:
    return [prefix + char]
  words = []
  for i in range(num_children):
    words += read_payload_trie(bits, symbols, tables, depth+1, prefix + char)
  return words

def read_payload(bits, symbols, tables):
  word = ''
  for i in range(len(tables)):
    symbol = bits.read_varint(tables[i])
    word += symbols[symbol]
  return word

def decode(bits, symbols, use_trie):
  bits = BitStream(bits)
  # Header.
  table_size = bits.read_int(8)
  word_size = bits.read_int(8)
  num_tables = bits.read_int(8)
  num_symbols = bits.read_int(16)

  print("Table Size Bits:", table_size)
  print("Huffman Table Word Bits:", word_size)
  print("Num Tables:", num_tables)
  print("Num Symbols:", num_symbols)

  tables = []
  for i, table_id in enumerate(range(num_tables)):
    num_items = bits.read_int(table_size)
    print("Table {}:".format(i), num_items)

    table = {}
    for j in range(num_items):
      char = bits.read_int(word_size)
      encoding_size = bits.read_int(8)
      encoding = bits.read(encoding_size)
      table[encoding] = char
    tables.append(table)

  words = []
  for alpha in range(num_symbols):
    if use_trie:
      words += read_payload_trie(bits, symbols, tables)
    else:
      words.append(read_payload(bits, symbols, tables))
  return words

if __name__ == "__main__":
  with open('wordle.json', 'r') as fp:
    words = json.load(fp)

  def gram_1(x):
    return x

  def gram_2(x):
      return [x[0], x[1], x[2], x[3:]]

  func = gram_1
  use_trie = True

  if func == gram_1:
    INT_MAP = dict(zip(
      list('abcdefghijklmnopqrstuvwxyz'),
      range(26)
    ))
  elif func == gram_2:
    INT_MAP = dict(zip(
      list('abcdefghijklmnopqrstuvwxyz') +
      [x[0]+x[1] for x in itertools.product(*['abcdefghijklmnopqrstuvwxyz'] * 2)],
      range(702)
    ))

  if use_trie:
    trie = {}
    for word in words:
      node = trie
      for letter in func(word):
        if letter not in node:
          node[letter] = {}
        node = node[letter]

  tables = []
  for i in range(len(func(words[0]))):
    if use_trie:
      string = leaves_at_depth(trie, i)
    else:
      string = [func(x)[i] for x in words]
    freqs = count_frequencies(string)
    tree = construct_frequency_tree(freqs)
    huff = generate_huffman_code(tree[0][0], [])
    total = sum([x[1] for x in freqs])
    smaller = 0
    bigger = 0
    for k, v in sorted(freqs, key=lambda x: x[1], reverse=True):
      if len(huff[k]) < 5:
        smaller += v
      if len(huff[k]) > 5:
        bigger += v
      print("{} | {} | {} | {:0.1f}%".format(k, "".join(map(str, huff[k])), v,
        v/total*100))
    print("Smaller: {:0.1f}%".format(smaller / total * 100))
    print("Bigger: {:0.1f}%".format(bigger / total * 100))
    print("")
    tables.append(huff)

  if use_trie:
    string = []
    count_children_trie(trie, string)
    freqs = count_frequencies(string)
    tree = construct_frequency_tree(freqs[1:])
    huff = generate_huffman_code(tree[0][0], [])
    total = sum([x[1] for x in freqs[1:]])
    smaller = 0
    bigger = 0
    print(huff, freqs)
    for k, v in sorted(freqs[1:], key=lambda x: x[1], reverse=True):
      if len(huff[k]) < 5:
        smaller += v
      if len(huff[k]) > 5:
        bigger += v
      print("{} | {} | {} | {:0.1f}%".format(k, "".join(map(str, huff[k])), v,
        v/total*100))
    print("Smaller: {:0.1f}%".format(smaller / total * 100))
    print("Bigger: {:0.1f}%".format(bigger / total * 100))
    print("")

    tables.append(huff)

  bits = BitStream(BitArray(), char_map=INT_MAP)
  table_size = bits_needed_to_represent(max_len_table(tables))
  word_size = bits_needed_to_represent(len(INT_MAP))
  num_tables = len(tables)
  if use_trie:
    num_symbols = len(tables[0])
  else:
    num_symbols = len(words)

  # Header.
  bits.write(table_size, 8)
  bits.write(word_size, 8)
  bits.write(num_tables, 8)
  bits.write(num_symbols, 16)

  # Encode the Huffman tables.
  header_size = len(bits)
  for table in tables:
    bits.write(len(table), table_size)
    for char, binary in table.items():
      bits.write(char, word_size)
      bits.write(len(binary), 8)
      bits.append(binary)
  huff_size = len(bits) - header_size

  # Encode the payload.
  if use_trie:
    max_children = max_children_trie(trie)
    convert_trie_to_bits(trie, bits.bits, tables, smart=True)
  else:
    for word in words:
      for i, char in enumerate(func(word)):
        binary = tables[i][char]
        bits.append(binary)

  payload_size = len(bits) - huff_size

  print("#")
  print("# Encoding")
  print("#")
  print("")

  print("Table Size Bits:", table_size)
  print("Huffman Table Word Bits:", word_size)
  print("Num Tables:", num_tables)
  print("Num Symbols", num_symbols)
  for i, table in enumerate(tables):
    print("Table {}:".format(i), len(table))

  print("")
  print("Header (Bytes):", math.ceil(header_size / 8))
  print("Tables (Bytes):", math.ceil(huff_size / 8))
  print("Payload (Bytes):", math.ceil(payload_size / 8))
  print("Filesize (Bytes):", math.ceil(len(bits) / 8))

  with open("wordle_{}.bin".format(func.__name__), "wb") as fp:
    fp.write(bits.bits.tobytes())

  print("")
  print("#")
  print("# Decoding")
  print("#")
  print("")

  s = time.monotonic()
  words = decode(bits.bits, list(INT_MAP.keys()), use_trie)
  print("")
  print("Num Words Decoded:", len(words))
  print("First Word:", words[0])
  print("Last Word:", words[-1])
  print("Decode Time: {:0.3f}s".format(time.monotonic() - s))
