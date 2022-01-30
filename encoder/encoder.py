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

class WordleHuffmanTrie:
  def __init__(self):
    self.bits = None
    self.table_size = 0
    self.word_size = 0
    self.num_tables = 0
    self.num_symbols = 0
    self.header_size = 0
    self.huff_size = 0
    self.payload_size = 0
    self.huffs = []
    self.tables = []

  def encode(self, words, symbols):
    self.words = words
    self.symbols = symbols
    trie = Trie(self.words)

    for i in range(len(self.words[0])):
      string = trie.leaves_at_depth(i)
      huff = Huffman(string)
      self.huffs.append(huff)
      self.tables.append(huff.code)

    string = trie.count_children()
    huff = Huffman(string, ignore=[0])
    self.huffs.append(huff)
    self.tables.append(huff.code)

    self.bits = BitReader(BitArray(), char_map=self.symbols)
    self.table_size = bit_size(max([len(code) for code in self.tables]))
    self.word_size = bit_size(len(self.symbols))
    self.num_tables = len(self.tables)
    self.num_symbols = max([len(table) for table in self.tables])

    # Header.
    self.bits.write(self.table_size, 8)
    self.bits.write(self.word_size, 8)
    self.bits.write(self.num_tables, 8)
    self.bits.write(self.num_symbols, 16)

    # Encode the Huffman tables.
    self.header_size = len(self.bits)
    for table in self.tables:
      self.bits.write(len(table), self.table_size)
      for char, binary in table.items():
        self.bits.write(char, self.word_size)
        self.bits.write(len(binary), 8)
        self.bits.append(binary)
    self.huff_size = len(self.bits) - self.header_size

    # Encode the payload.
    self._encode_trie(trie.trie)

    self.payload_size = len(self.bits) - self.huff_size

  def _encode_trie(self, trie, depth=0):
    for k, v in trie.items():
      if v.keys():
        self.bits.append(self.tables[-1][len(v.keys())])
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

    words = []
    for alpha in range(self.num_symbols):
      words += self._read_payload()
    self.payload_size = self.bits.i - self.huff_size
    return words

  def _read_payload(self, depth=0, prefix=''):
    num_children = 0
    if depth < len(self.tables) - 2:
      num_children = self.bits.read_varint(self.tables[-1])
    symbol = self.bits.read_varint(self.tables[depth])
    char = self.symbols[symbol]
    if depth == len(self.tables) - 2:
      return [prefix + char]
    words = []
    for i in range(num_children):
      words += self._read_payload(depth+1, prefix + char)
    return words

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
  args = sys.argv[1:]
  argc = len(args)
  filename = args[0] or 'wordle.json'
  with open(filename, 'r') as fp:
    words = json.load(fp)

  INT_MAP = dict(zip(
    list('abcdefghijklmnopqrstuvwxyz'),
    range(26)
  ))

  verify = argc == 2
  trie = WordleHuffmanTrie()
  trie.encode(words, INT_MAP)
  #trie.print_huffman_stats()
  trie.print_debug()

  with open("words.bin", "wb") as fp:
    fp.write(trie.tobytes())

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
