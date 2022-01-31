from bitstring import BitArray
import json
import math
import sys
import time

from bit_reader import BitReader
from huffman import Huffman
from trie import Trie

def bit_size(num):
  return math.ceil(math.log2(num))

def bit_round(num):
  for x in [8, 16, 32, 64]:
    if num < x:
      return x
  return num

class WordleHuffmanTrie:
  def __init__(self, variable_length=False):
    self.bits = None
    self.table_size = 0
    self.word_size = 0
    self.num_tables = 0
    self.num_symbols = 0
    self.header_size = 0
    self.huff_size = 0
    self.payload_size = 0
    self.i = 0
    self.huffs = []
    self.tables = []
    self.variable_length = variable_length

  def encode(self, words, symbols):
    self.words = words
    self.symbols = symbols
    trie = Trie(self.words, variable_length=self.variable_length)

    for i in range(max([len(x) for x in self.words])):
      string = trie.leaves_at_depth(i)
      huff = Huffman(string)
      self.huffs.append(huff)
      self.tables.append(huff.code)

    string = trie.count_children()
    ignore = [] if self.variable_length else [0]
    huff = Huffman(string, ignore=ignore)
    self.huffs.append(huff)
    self.tables.append(huff.code)

    self.bits = BitReader(BitArray(), char_map=self.symbols)
    self.table_size = bit_size(max([len(code) for code in self.tables]))
    self.word_size = bit_size(len(self.symbols))
    self.num_tables = len(self.tables)
    self.num_symbols = len(self.tables[0])

    # Header.
    self.bits.write(self.table_size, 8)
    self.bits.write(self.word_size, 8)
    self.bits.write(self.num_tables, 8)
    self.bits.write(self.num_symbols, 16)

    # Encode the Huffman tables.
    self.header_size = len(self.bits)
    for table in self.tables:
      table_len = len(table)
      if self.variable_length and 'END' in table:
        table_len -= 1
      self.bits.write(table_len, self.table_size)
      for char, binary in table.items():
        if self.variable_length and char == 'END':
          continue
        self.bits.write(char, self.word_size)
        self.bits.write(len(binary), 8)
        self.bits.append(binary)
    self.huff_size = len(self.bits) - self.header_size
    self.i = len(self.bits) + 1

    # Encode the payload.
    self._encode_trie(trie.trie)

    self.payload_size = len(self.bits) - self.huff_size

  def _encode_trie(self, trie, depth=0):
    for k, v in trie.items():
      if self.variable_length and k == 'END':
        continue
      if self.variable_length or v:
        len_v = len(v)
        if self.variable_length and 'END' in v:
          len_v -= 1
        self.bits.append(self.tables[-1][len_v])
      if self.variable_length:
        self.bits.write(1 if 'END' in v else 0, 1)
      self.bits.append(self.tables[depth][k])
      self._encode_trie(v, depth+1)

  def decode(self, bits, symbols):
    self.bits = BitReader(bits)
    self.symbols = symbols

    # Header.
    self.table_size = self.bits.read_int(8)
    self.word_size = self.bits.read_int(8)
    self.num_tables = self.bits.read_int(8)
    self.num_symbols = self.bits.read_int(16)
    self.header_size = self.bits.i

    self.tables = []
    for i in range(self.num_tables):
      num_items = self.bits.read_int(self.table_size)
      table = {}
      for j in range(num_items):
        char = self.bits.read_int(self.word_size)
        encoding_size = self.bits.read_int(8)
        encoding = self.bits.read(encoding_size)
        table[encoding] = char
      self.tables.append(table)
    self.huff_size = self.bits.i - self.header_size
    self.i = self.bits.i

    words = []
    for alpha in range(self.num_symbols):
      words += self._read_payload()
    self.payload_size = self.bits.i - self.huff_size
    return words

  def word_indices(self, words):
    self.bits.i = self.i
    count = 0
    res = []
    for alpha in range(self.num_symbols):
      count, new_words = self._index_of_payload(words, count)
      res += new_words
    return res

  def _read_payload(self, depth=0, prefix=''):
    num_children = 0
    if self.variable_length or depth < len(self.tables) - 2:
      num_children = self.bits.read_varint(self.tables[-1])
    terminates = self.bits.read_int(1) if self.variable_length else False
    symbol = self.bits.read_varint(self.tables[depth])
    char = self.symbols[symbol]

    if ((self.variable_length and num_children == 0) or
        (depth == len(self.tables) - 2)):
      return [prefix + char]

    words = []
    if self.variable_length and terminates:
      words.append(prefix + char)

    for i in range(num_children):
      words += self._read_payload(depth+1, prefix + char)
    return words

  def _index_of_payload(self, words, count=0, depth=0, prefix=''):
    num_children = 0
    if depth < len(self.tables) - 2:
      num_children = self.bits.read_varint(self.tables[-1])
    symbol = self.bits.read_varint(self.tables[depth])
    char = self.symbols[symbol]
    if depth == len(self.tables) - 2:
      count += 1
      if prefix + char in words:
        return count, [(prefix + char, count)]
      return count, []
    res = []
    for i in range(num_children):
      count, new_words = self._index_of_payload(words, count, depth+1, prefix + char)
      res += new_words
    return count, res

  def print_debug(self):
    print("Table Size Bits:", self.table_size)
    print("Huffman Table Word Bits:", self.word_size)
    print("Num Tables:", self.num_tables)
    print("Num Symbols", self.num_symbols)
    for i, table in enumerate(self.tables):
      print("Table {}:".format(i), len(table))
    print("")
    print("Header (Bytes):", math.ceil(self.header_size / 8))
    print("Tables (Bytes):", math.ceil(self.huff_size / 8))
    print("Payload (Bytes):", math.ceil(self.payload_size / 8))
    print("Filesize (Bytes):", math.ceil(len(self.bits) / 8))
    print("")

  def print_huffman_stats(self):
    for i, huff in enumerate(self.huffs):
      print("Huffman Table: {}".format(i+1))
      total = sum([x[1] for x in huff.freqs])
      smaller = 0
      bigger = 0
      for k, v in sorted(huff.freqs, key=lambda x: x[1], reverse=True):
        if len(huff.code[k]) < 5:
          smaller += v
        if len(huff.code[k]) > 5:
          bigger += v
        print("{} | {} | {} | {:0.1f}%".format(k, "".join(map(str, huff.code[k])), v,
          v/total*100))
      print("Smaller: {:0.1f}%".format(smaller / total * 100))
      print("Bigger: {:0.1f}%".format(bigger / total * 100))
      print("")

  def tobytes(self):
    return self.bits.bits.tobytes()


if __name__ == "__main__":
  with open('../common/wordle.json', 'r') as fp:
    all_words = json.load(fp)

  INT_MAP = dict(zip(
    list('abcdefghijklmnopqrstuvwxyz'),
    range(26)
  ))

  trie = WordleHuffmanTrie(variable_length=False)
  words = all_words
  trie.encode(words, INT_MAP)
  trie.print_debug()
  with open("words.bin", "wb") as fp:
    fp.write(trie.tobytes())

  s = time.monotonic()
  trie2 = WordleHuffmanTrie(variable_length=False)
  words = trie2.decode(trie.bits.bits, list(INT_MAP.keys()))
  print("# Verification")
  print("Num Words Decoded:", len(words))
  print("Shortest Word:", min([len(x) for x in words]))
  print("Longest Word:", max([len(x) for x in words]))
  print("First Word:", words[:10])
  print("Last Word:", words[-10:])
  print("Decode Time: {:0.3f}s".format(time.monotonic() - s))

  sys.exit()

  for i in range(2, 12):
    trie = WordleHuffmanTrie()
    words = [x for x in all_words if len(x) == i]
    trie.encode(words, INT_MAP)
    trie.print_debug()
    with open("hellowordl_{}.bin".format(i), "wb") as fp:
      fp.write(trie.tobytes())

    s = time.monotonic()
    trie2 = WordleHuffmanTrie()
    words = trie2.decode(trie.bits.bits, list(INT_MAP.keys()))
    print("# Verification")
    print("Num Words Decoded:", len(words))
    print("First Word:", words[0])
    print("Last Word:", words[-1])
    print("Decode Time: {:0.3f}s".format(time.monotonic() - s))

  sys.exit()

  args = sys.argv[1:]
  argc = len(args)
  filename = args[0] or '../common/wordle.json'
  with open(filename, 'r') as fp:
    words = json.load(fp)

  filename = args[1] or '../common/wordle_answers.json'
  with open(filename, 'r') as fp:
    answers = json.load(fp)

  words += answers

  INT_MAP = dict(zip(
    list('abcdefghijklmnopqrstuvwxyz'),
    range(26)
  ))

  verify = argc == 3
  trie = WordleHuffmanTrie()
  trie.encode(words, INT_MAP)
  #trie.print_huffman_stats()
  trie.print_debug()

  trie2 = WordleHuffmanTrie()
  words = trie2.decode(trie.bits.bits, list(INT_MAP.keys()))

  with open("words.bin", "wb") as fp:
    fp.write(trie.tobytes())

  day_offset = 225
  day_count = 30 % 256
  answer_set = answers[day_offset:day_offset+day_count]
  answer_idxs = dict(trie2.word_indices(answer_set))
  idxs = [answer_idxs[answer] for answer in answer_set]

  bits = BitReader(BitArray())
  num_bits = bit_round(bit_size(len(words)-1))
  bits.write(day_offset, 16) # 66,536 days total.
  bits.write(day_count, 8) # 256 days max.
  for idx in idxs:
    bits.write(idx, num_bits)
  print(idxs, answer_set, answer_idxs)
  print("Answers written in {}bit".format(num_bits))

  with open("answers.bin", "wb") as fp:
    fp.write(bits.bits.tobytes())

  if verify:
    s = time.monotonic()
    trie2 = WordleHuffmanTrie()
    words = trie2.decode(trie.bits.bits, list(INT_MAP.keys()))
    #trie2.print_debug()
    print("# Verification")
    print("Num Words Decoded:", len(words))
    print("First Word:", words[0])
    print("Last Word:", words[-1])
    print("Decode Time: {:0.3f}s".format(time.monotonic() - s))
