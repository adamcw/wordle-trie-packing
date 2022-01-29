import json
import packed_pb2

INT_MAP = dict(zip(
  'abcdefghijklmnopqrstuvwxyz',
  range(26)
))

print(INT_MAP)

with open('wordle.json', 'r') as fp:
  words = json.load(fp)

wordle_dict = packed_pb2.WordleDict()
for word in words:
  for letter in word:
    wordle_dict.letter.append(INT_MAP[letter])

with open('wordle.proto', 'wb') as fp:
  fp.write(wordle_dict.SerializeToString())
