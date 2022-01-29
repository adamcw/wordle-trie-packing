from bitstring import BitArray
import json

INT_MAP = dict(zip(
  'abcdefghijklmnopqrstuvwxyz',
  range(26)
))

with open('wordle.json', 'r') as fp:
  words = json.load(fp)

letters = [letter for word in words for letter in word]
values = [INT_MAP[letter] for letter in letters]

bits = []
for letter in letters:
  val = INT_MAP[letter]
  mask = 0b00010000
  for i in range(5):
    bits.append((val & mask) >> 4 - i)
    mask >>= 1

byte_array = BitArray(bits)
byte_string = byte_array.tobytes()

with open('wordle.bin', 'wb') as fp:
  fp.write(byte_string)

# Some debug functions for sanity checking.
def get_index(idx):
  return letters[idx], values[idx], bits[idx*5:idx*5+5]

for i in range(5):
  print(get_index(i))
