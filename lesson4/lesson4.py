import json
import packed_pb2

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

#
# JSON Solution.
#
with open('wordle_trie.json', 'w') as fp:
  json.dump(trie, fp)

#
# Proto Solution.
#
def convert_trie_to_proto(trie, proto_trie):
  for k, v in trie.items():
    new = proto_trie.nodes.add()
    new.letter = INT_MAP[k]
    convert_trie_to_proto(v, new)

proto_trie = packed_pb2.WordleTrie()
convert_trie_to_proto(trie, proto_trie)

with open('wordle_trie.proto', 'wb') as fp:
  fp.write(proto_trie.SerializeToString())

#
# String Solution.
#
def convert_trie_to_str(trie, str_trie):
  for k, v in trie.items():
    str_trie.append(str(len(v.keys())))
    str_trie.append(k)
    convert_trie_to_str(v, str_trie)

str_trie = []
convert_trie_to_str(trie, str_trie)
str_trie = "".join(str_trie)

with open('wordle_trie.txt', 'w') as fp:
  fp.write(str_trie)

#
# String Solution, Smarter.
#
def convert_trie_to_str(trie, str_trie):
  for k, v in trie.items():
    if v.keys():
      str_trie.append(str(len(v.keys())))
    str_trie.append(k)
    convert_trie_to_str(v, str_trie)

str_trie = []
convert_trie_to_str(trie, str_trie)
str_trie = "".join(str_trie)

with open('wordle_trie_smart.txt', 'w') as fp:
  fp.write(str_trie)
