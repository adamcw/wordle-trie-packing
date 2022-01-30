import collections
import json

with open('../common/wordle.json', 'r') as fp:
  words = json.load(fp)

with open('../common/wordle_answers.json', 'r') as fp:
  words += json.load(fp)

def count_frequencies(string):
  freq = collections.defaultdict(int)
  for char in string:
    freq[char] += 1
  return sorted(freq.items(), key=lambda x: x[1], reverse=True)

def not_in(exclude, word):
  for i in exclude:
    if isinstance(i, str):
      if i in word:
        return False
    else:
      i, position = i
      if word[position-1] == i:
        return False
  return True

def has_in(include, word):
  for i in include:
    if isinstance(i, str):
      if i not in word:
        return False
    else:
      i, position = i
      if word[position-1] != i:
        return False
  return True

include = ["u", ("l", 4)]
exclude = ["p", "e", "r" , "t", "y", "i", "p", "a", "s", "g", "h", "b", "m", ("u", 2), ("l", 1)]

include = []
exclude = []

valid_words = [x for x in words if not_in(exclude, x) and has_in(include, x)]

letters = "".join(valid_words)
freqs = count_frequencies(letters)
print("# Overall Best")
for letter, freq in freqs[:5]:
  print("{}: {}".format(letter, freq))

print("# Overall Worst")
for letter, freq in freqs[-5:]:
  print("{}: {}".format(letter, freq))

for i in range(5):
  letters = [word[i] for word in valid_words]
  freqs = count_frequencies(letters)
  print("# Position {} Best".format(i+1))
  for letter, freq in freqs[:5]:
    print("{}: {}".format(letter, freq))

  print("# Position {} Worst".format(i+1))
  for letter, freq in freqs[-5:]:
    print("{}: {}".format(letter, freq))
