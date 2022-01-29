from bitstring import BitArray
import json

INT_MAP = dict(zip(
  'abcdefghijklmnopqrstuvwxyz',
  range(26)
))

with open('wordle.json', 'r') as fp:
  words = json.load(fp)

trie = {}
for word in words:
  node = trie
  for letter in word:
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

def convert_trie_to_bits(trie, bit_trie, n_index_bits, smart=False):
  for k, v in trie.items():
    if not smart or v.keys():
      bit_trie.append(key_to_bits(len(v.keys())))
    bit_trie.append(key_to_bits(k))
    convert_trie_to_bits(v, bit_trie, n_index_bits, smart=smart)

bit_trie = BitArray()
bit_trie_smart = BitArray()
max_children = max_children_trie(trie)
n_index_bits = bits_needed_to_represent(max_children)
convert_trie_to_bits(trie, bit_trie, n_index_bits, smart=False)
convert_trie_to_bits(trie, bit_trie_smart, n_index_bits, smart=True)

byte_string = bit_trie.tobytes()
byte_string_smart = bit_trie_smart.tobytes()

with open('wordle_trie.bin', 'wb') as fp:
  fp.write(byte_string)

with open('wordle_trie_smart.bin', 'wb') as fp:
  fp.write(byte_string_smart)
