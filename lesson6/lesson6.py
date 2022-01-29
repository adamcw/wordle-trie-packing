from bitstring import BitArray
import itertools
import json

def gram_1(x):
  return x

def gram_2(x):
  return [x[:1], x[1:3], x[3:]]

def gram_3(x):
  return [x[:2], x[2:]]

def gram_4(x):
  return [x[0], x[1:]]

def gram_5(x):
  return [x]

for func in [gram_1, gram_2, gram_3, gram_4, gram_5]:
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
  elif func == gram_3:
    INT_MAP = dict(zip(
      [x[0]+x[1] for x in itertools.product(*['abcdefghijklmnopqrstuvwxyz'] * 2)] +
      [x[0]+x[1]+x[2] for x in itertools.product(*['abcdefghijklmnopqrstuvwxyz'] * 3)],
      range(18252)
    ))
  elif func == gram_4:
    INT_MAP = dict(zip(
      list('abcdefghijklmnopqrstuvwxyz') +
      [x[0]+x[1]+x[2]+x[3] for x in itertools.product(*['abcdefghijklmnopqrstuvwxyz'] * 4)],
      range(457002)
    ))
  elif func == gram_5:
    INT_MAP = dict(zip(
      [x[0]+x[1]+x[2]+x[3]+x[4] for x in itertools.product(*['abcdefghijklmnopqrstuvwxyz'] * 5)],
      range(11881376)
    ))

  with open('wordle.json', 'r') as fp:
    words = json.load(fp)

  trie = {}
  for word in words:
    node = trie
    for letter in func(word):
      if letter not in node:
        node[letter] = {}
      node = node[letter]

  def key_to_bits(key, n_bits=5):
    bits = []
    val = INT_MAP[key] if isinstance(key, str) else key
    mask = 0b1 << n_bits
    for i in range(n_bits):
      bits.append((val & mask) >> n_bits - 1 - i)
      mask >>= 1
    return bits

  def max_children_trie(trie):
    max_len = 0
    for k, v in trie.items():
      v_len = len(v.keys())
      max_len = max(max_len, v_len)
      max_len = max(max_len, max_children_trie(v))
    return max_len

  # This will always return five for original Wordle dictionaries, however fewer
  # bits may be needed if dictionaries are small.
  def bits_needed_to_represent(num):
    mask = 0b1 << 32
    for i in range(32):
      if (((num & mask) >> 31 - i)):
        return 32 - i + 1;
      mask >>= 1
    return 0

  def convert_trie_to_bits(trie, bit_trie, n_key_bits, n_index_bits, smart=False):
    for k, v in trie.items():
      if not smart or v.keys():
        bit_trie.append(key_to_bits(len(v.keys()), n_index_bits))
      bit_trie.append(key_to_bits(k, n_key_bits))
      convert_trie_to_bits(v, bit_trie, n_key_bits, n_index_bits, smart=smart)

  bit_trie = BitArray()
  bit_trie_smart = BitArray()
  max_children = max_children_trie(trie)
  n_key_bits = bits_needed_to_represent(len(INT_MAP))
  n_index_bits = bits_needed_to_represent(max_children)
  convert_trie_to_bits(trie, bit_trie, n_key_bits, n_index_bits, smart=False)
  convert_trie_to_bits(trie, bit_trie_smart, n_key_bits, n_index_bits, smart=True)

  print("{} {} {} {}".format(func.__name__, n_key_bits, n_index_bits,
    bits_needed_to_represent(8)))

  byte_string = bit_trie.tobytes()
  byte_string_smart = bit_trie_smart.tobytes()

  with open('wordle_trie_{}.bin'.format(func.__name__), 'wb') as fp:
    fp.write(byte_string)

  with open('wordle_trie_{}_smart.bin'.format(func.__name__), 'wb') as fp:
    fp.write(byte_string_smart)
