# Wordle Trie Packing

Wordle clones are everywhere, but who is thinking about the bandwidth?

## What is Wordle?

[Wordle](https://www.powerlanguage.co.uk/wordle) is a word game with
elements of [Mastermind](https://en.wikipedia.org/wiki/Mastermind_(board_game)).

You get six turns to guess a five letter target word, each turn you must enter a
valid five letter word. If a letter in that word is in the target word, but not
in the correct position it will be yellow, if it's in the target word in the
same position it is green (or colorblind equivalents). If you guessed the
correct word, all five letters will be green. The goal is to get the correct
word in as few words as possible.

## Problem Background

The Wordle source on 2022-01-29 was served
[Brotli](https://en.wikipedia.org/wiki/Brotli) encoded in 39,912 bytes, which
uncompressed is 177,553 bytes of minified JavaScript (60,303 bytes gzipped).

In this source code, there exists two arrays. One for valid dictionary words,
and one with answers. There are 2,315 answers and 10,657 valid dictionary words,
both sets are combined in the game to form a super-dictionary of 12,972 words.
The answers have been omitted from this repository/analysis to at least pretend
to protect the integrity of the game.

The valid dictionary words take up 85,258 bytes uncompressed, or ~48% of the
total source size. Compressed on its own with Brotli encoding, this becomes
14,704 bytes.

Removing both dictionaries from the source and Brotli to compress it back,
results in a reduction to 18,461 bytes (46% of original compressed size), or
21,451 bytes are dedicated to the dictionaries. This means even with the high
compression, these dictionaries alone account for half the bandwidth.

## Problem Statement

How small can we represent the valid dictionary words, and can we beat Brotli
compression by attempting to make a custom file format that leverages the very
specific nature of the Wordle dictionary.

## Lesson 1: JSON is Big

By including the dictionary in their JavaScript source, this is equivalent to
storing the dictionary in [JSON](https://en.wikipedia.org/wiki/JSON) (JavaScript
Object Notation) format.

```
['worda', wordb', 'wordc']
```

All words in Wordle are the same length. This means that you can store them in
one large contiguous string. Further, all characters are lowercase and only
between [a-z]. You can simply iterate this large string jumping n-characters
(five in the original Wordle) to find if a word is in the dictionary.

We can therefore remove the square brackets, quotation marks and commas that
make up the original JSON string.

```
wordawordbwordc
```

Uncompressed this is 53,286 bytes (37.5% saving) and Brotli compresses to 14,639
bytes (0.4% saving). We can see this format saves little on bandwidth, but would
save a notable amount of application memory.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Super String                   | 53,286       | 14,639              |

## Lesson 2: Protobufs

[Protobufs](https://developers.google.com/protocol-buffers/docs/pythontutorial)
(Protocol Buffers) leverage varints (variable length integers) to allow them to
efficiently pack integers based on their size. We can convert the letters [a-z]
to the numbers 0-26, then pack them in a protobuf.

This gives us 53,289 bytes (37.5% saving) uncompressed, and 14,976 bytes Brotli
encoded. Compared to the super-string in Lesson 1, this is three bytes worse
uncompressed, and 337 bytes worse compressed.

Uncompressed, this makes sense, the packed protobuf format still represents an
integer with [at least eight
bits](https://developers.google.com/protocol-buffers/docs/encoding#varints),
this is the same size as a char. The extra three bytes will be the header for
the protobuf.

```
abc -> 0000 0000 0000 0001 0000 0010
```

This means, if we want to do better uncompressed, we need to do better than 8
bits per character. If we want to do better compressed, we're going to have to
come up with a more compact encoding scheme than the general approach taken by
Brotli.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Super String                   | 53,286       | 14,639              |
| Protobuf String                | 53,289       | 14,639              |

## Lesson 3: Bitpacking

The numbers 0-25 can be represented with only five bits (`2^5 = 32`), rather
than eight, a 37.5% size reduction. If we convert each character to an integer,
then pack these into a binary format this way, we can get a notable uncompressed
size saving.

```
abc -> 00000 00001 00010
```

This produces a binary format that is 33,304 bytes uncompressed (37.5% saving
over a super string, and 60.9% saving over the original JSON.

Unfortunately, this compresses really poorly. Brotli encoding produces 30,977
bytes, or more than doubles the network size. This format could therefore be
considered for memory optimization, but not bandwidth. The super-string method
would be best to transfer the file, then this format could be used to store the
dictionary in memory (in a world where we want to play Wordle and care about
saving just under 20KB of memory).

This also suggests a reason protobufs prefer to remain byte-aligned with their
varints. Not only is byte-aligned data easier to deal with, but they also allow
for structure in the input to remain in the output which can be leveraged by
compression algorithms over-the-wire (the data as represented while in transit
between two places).

Compression differs from general bitpacking in that compression generally needs
to be uncompressed for the data to be useful. In comparison, bitpacking will
take a data structure and just condense how many bits are required to represent
it. This may slow down the use of the data structure due to having to unpack as
you go, but it doesn't require a full decompress step before any action on the
data can be taken.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Super String                   | 53,286       | 14,639              |
| Protobuf String                | 53,289       | 14,639              |
| Bitpacked String               | 33,304       | 30,977              |

## Lesson 4: Tries

A [Trie](https://en.wikipedia.org/wiki/Trie) is essentially a prefix-tree. That
is, you can encode the words MOUNT and MOUTH as the following tree:

```
             T - H
            /
M - O - U -
            \
             N - T
```

Each letter needs to track both itself, as well as a list of suffixes.
Therefore, a trie can be a very expensive data structure and is generally used
for more efficient lookup of if a word exists, than to save memory.

We can utilize some knowledge of the structure to try and pack it more
efficiently though, and see if we can save more from reducing the number of
letters overall, than we add in upkeep needing to track the suffix nodes.

### Trie (JSON)

As discussed in Lesson 1, JSON is very inefficient in terms of size. Encoding
the trie into JSON resulted in a filesize of 170,785 bytes uncompressed and
17,070 bytes Brotli encoded. Uncompressed it is more than twice as big as the
original JSON representation, and slightly larger when compressed as well. I
won't waste any more of your life on this attempt.

### Trie (Protobuf)

Protobufs offer reasonable packing of integers, and can represent nested data
fairly efficiently as well. Converting the trie to protobuf results in an
uncompressed size of 82,642 bytes and a Brotli compressed size of 19,196 bytes.

Uncompressed this is marginally better than baseline, but it compresses worse,
and performs worse than substantially easier-to-work-with solutions such as a
basic Super String from Lesson 1.

### Trie (String)

We know that strings seem to compress much better than bitpacked/binary data, so
what if we just represented the trie in a plain-text format. At this point we
will lose the ability to navigate the trie without parsing the full thing. This
will make lookups horribly inefficient, but we don't care about that, we just
want to make things small!

MOUTH and MOUNT would be represented as follows:

```
1M1O2U1T0H1N0T
```

Each node writes down how many children it has, followed by the letter. To
decode this, you traverse down each node until you have seen N children, then
you go back up the stack and keep traversing. This method is very slow to look
up words that are prefixed with later letters like Z. You could somewhat
optimize the lookup time (if we cared about such things) by writing the prefixes
in an order proportional to their probability at each level.

This produces uncompressed 43,917 bytes and 15,584 bytes Brotli compressed.
However, we can leverage the fact we know all strings are the same length and
omit and of the 0s on the tail nodes.

```
1M1O2U1TH1NT
```

This "Smart" approach, produces 32,260 bytes uncompressed, and 14,562 Brotli
compressed. Making this approach both smaller than the original bitpacked
version in Lesson 3, as well as being smaller when compressed than any prior
method.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Trie (JSON)                    | 170,785      | 17,070              |
| Trie (Protobuf)                | 82,642       | 19,196              |
| Trie (String)                  | 42,917       | 15,584              |
| Trie (String, Smart)           | 32,260       | 14,562              |

## Lesson 5: The Kitchen Sink

We've seen from Lesson 3 that bitpacking produces very small uncompressed files
compared to the same data not bitpacked. Further, we've seen in Lesson 4 that a
Trie in Smart String format can be very small.

Naturally the question is, what if we bitpacked this datastructure?

Each letter is five bits as before, with the number of children being a maximum
of 26 as well, requiring another five bits. We then follow the encoding method
in Lesson 4 exactly, but writing ten bits per node instead of 16-24 (integers
greater than nine require two eight bit characters to represent in plain text).

This produces 26,692 bytes uncompressed and 14,092 bytes Brotli compressed, when
we don't leverage the "Smart" modification. With the "Smart" modification we get
20,031 bytes uncompressed and 15,070 bytes compressed.

What does this suggest? This method produces by far the smallest uncompressed
file being a mere 23.5% the size of the original using the "Smart" modification.
With and without the "Smart" modification, this method is 2.5% worse or 4.3%
better than baseline when Brotli encoded.

The non-"Smart" encoding wins the smallest when Brotli encoded, and the "Smart"
encoding with the smallest when uncompressed.

This suggests that the extra zero-bits in the non-"Smart" version must add more
structure for the Brotli encoder to leverage for a better compression ratio.
The compression on this bitpacked structure is likely very input dependent, and
could vary if we re-ordered the keys in the trie.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Trie (String, Smart)           | 32,260       | 14,562              |
| Trie (Bitpacked)               | 26,692       | 14,092*             |
| Trie (Bitpacked, Smart)        | 20,031*      | 15,070              |

## Lesson 6: N-gram Tries

Letters in the English language don't all occur with the same frequency, either
on their own or in pairs. Utilizing a 1-gram trie as in Lessons 4 and 5, we have
multiple instances of "OU" and "TH" and "ST" repeated numerous times. This is
likely leveraged quite well by the Brotli compression when not using bitpacked
data, however this structure is lost during bitpacking.

If we instead build a trie with 2-grams (every combination of two letters), we
can represent each word with a tree that only has branches of length 3 (two
nodes representing a 2-gram and one node representing the last letter as a
1-gram).

This requires us to encode each key in the trie as one of 702 combinations (a-z
and aa-zz).

We can similarly do 3-gram with two letters and three letters, a 4-gram with
one letter and four letters, and finally a 5-gram.

A 5-gram simply replaces every word with a 24 bit number representing it, this
is one bit less expensive per word than encoding each character individually as
five bits. Notably, this also seems to compress substantially better than the
bitpacking we did in Lesson 3.

These results are largely unremarkable, other than the 2-gram "Smart" version
achieving the lowest ever uncompressed size of 19,340 bytes vs. the 20,031 bytes
of the 1-gram version.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Trie (String, Smart)           | 32,260       | 14,562              |
| Trie (Bitpacked)               | 26,692       | 14,092*             |
| Trie (Bitpacked, Smart)        | 20,031       | 15,070              |
| 2-Gram Trie (Bitpacked)        | 29,997       | 17,357              |
| 2-Gram Trie (Bitpacked, Smart) | 19,340*      | 17,067              |
| 3-Gram Trie (Bitpacked)        | 31,531       | 19,678              |
| 3-Gram Trie (Bitpacked, Smart) | 20,874       | 19,025              |
| 4-Gram Trie (Bitpacked)        | 40,062       | 21,210              |
| 4-Gram Trie (Bitpacked, Smart) | 25,408       | 22,484              |
| 5-Gram Trie (Bitpacked, Smart) | 31,971       | 18,204              |

## Lesson 7: Huffman Coding

What is Brotli encoding doing exactly? It's doing a few general-purpose
compression algorithms, but it's also doing [Huffman coding](https://en.wikipedia.org/wiki/Huffman_coding).

Huffman coding is a process of generating a prefix code known as a Huffman code.
Put more intuitively, it aims leverages the non-uniform distribution of symbols
in a string in order to allocate fewer bits to letters that appear a lot, and
more bits to those than appear infrequently. The code is generated such that no
code overlaps a prefix with another code, allowing for unambiguous decoding of
variable lengths.

Without Huffman coding, the best we could do per word was 24 bits in Lesson 6.

#### Overall 5 Best Letters

Letter | Occurrences
-|-
s | 6665
e | 6662
a | 5990
o | 4438
r | 4158

#### Overall 5 Worst Letters

Letter | Occurrences
-|-
v | 694
z | 434
j | 291
x | 288
q | 112

We can see that `s` is really common, while `q` is really uncommon. It makes no
sense to encode `q` with the same number of bits as `s` given the fact `s`
occurs 60 time more often!

We can further leverage the fact that letter frequencies are different depending
on their location in a word.

#### Position 1: 5 Best Letters

Letter | Occurrences
-|-
s | 1565
c | 922
b | 909
p | 859
t | 815

#### Position 1: 5 Worst Letters

Letter | Occurrences
-|-
y | 181
i | 165
z | 105
q | 78
x | 16

#### Position 5: 5 Best Letters

Letter | Occurrences
-|-
s | 3958
e | 1522
y | 1301
d | 823
t | 727

#### Position 5: 5 Worst Letters

Letter | Occurrences
-|-
b | 59
z | 32
v | 4
q | 4
j | 3

We can see that `s` is a really common letter to start words, while `y` is
really uncommon. Meanwhile at the end of words `s` also reigns supreme, while
`y` has gone from 5th most uncommon, to 3rd most common!

We can therefore encode each position in our word with a different Huffman code.

#### Position 1: Huffman Code

Letter | Huffman Code | Occurrences | %
-|-|-|-
s | 011 | 1199 | 11.3%
b | 1100 | 736 | 6.9%
c | 1011 | 724 | 6.8%
p | 1010 | 717 | 6.7%
t | 1000 | 666 | 6.2%
a | 0101 | 596 | 5.6%
m | 0100 | 586 | 5.5%
d | 0010 | 574 | 5.4%
g | 0001 | 523 | 4.9%
r | 0000 | 523 | 4.9%
l | 11111 | 489 | 4.6%
f | 11110 | 462 | 4.3%
h | 11100 | 420 | 3.9%
k | 11010 | 356 | 3.3%
w | 10010 | 330 | 3.1%
n | 00111 | 288 | 2.7%
e | 111011 | 231 | 2.2%
o | 111010 | 221 | 2.1%
v | 110111 | 199 | 1.9%
j | 110110 | 182 | 1.7%
y | 100111 | 175 | 1.6%
u | 001101 | 156 | 1.5%
i | 001100 | 131 | 1.2%
z | 1001101 | 102 | 1.0%
q | 10011001 | 55 | 0.5%
x | 10011000 | 16 | 0.2%

We can see that `s` through `b` all use fewer than five bits, representing 64.2%
of our characters. `n` through `l` use the same number of bits as naive
conversion. `i` through `q` then use more than five bits due to their rarity,
representing only 13.8% of characters.

#### Position 5: Huffman Code

Letter | Huffman Code | Occurrences | %
-|-|-|-
s | 11 | 3922 | 36.8%
e | 011 | 1098 | 10.3%
y | 001 | 937 | 8.8%
d | 1010 | 705 | 6.6%
a | 1000 | 616 | 5.8%
t | 0100 | 474 | 4.4%
r | 0000 | 461 | 4.3%
n | 10111 | 400 | 3.8%
o | 10011 | 331 | 3.1%
l | 10010 | 320 | 3.0%
i | 01010 | 269 | 2.5%
h | 00010 | 231 | 2.2%
k | 010111 | 146 | 1.4%
m | 010110 | 140 | 1.3%
g | 1011011 | 102 | 1.0%
c | 1011010 | 96 | 0.9%
p | 1011001 | 91 | 0.9%
u | 0001111 | 66 | 0.6%
x | 0001110 | 62 | 0.6%
f | 0001101 | 56 | 0.5%
b | 0001100 | 48 | 0.5%
w | 10110001 | 47 | 0.4%
z | 101100001 | 28 | 0.3%
v | 1011000000 | 4 | 0.0%
q | 10110000011 | 4 | 0.0%
j | 10110000010 | 3 | 0.0%

At position 5 the encoding is even more favourable. We have 77.1% of our
characters represented by fewer than five bits, while only 8.4% are more than
five bits.

A downside to Huffman coding is you also need to include the table mapping each
Huffman code back to the original character. We need five bits to represent the
character, eight bits to represent the potential bit length of the Huffman code,
followed by the Huffman code. We also need to include how many items are in the
table so we know when to stop searching. Overall, we can encode the five tables
necessary in 306 bytes, with 5 bytes of additional header information.

To encode the payload, we can then loop through each letter in our document and
replace it with our Huffman code for that character in that position.

Doing this we get 27,057 bytes uncompressed and 26,748 bytes Brotli encoded.
Sadly, this doesn't compete with the tries on uncompressed size, and is one of
the worst when it comes to compressed size. We need to bring back the kitchen
sink and get to work.

| Attempt                        | Uncompressed   | Compressed (Brotli) |
|---------                       | ------------   | ------------------- |
| Base                           | 85,258         | 14,704              |
| Super String                   | 53,286         | 14,639              |
| 2-Gram Trie (Bitpacked, Smart) | 19,340         | 17,067              |
| Huffman (Bitpacked)            | 27,057         | 27,678              |

## Lesson 7 Continued: The Huffman Coded Bitpacked Smart Trie

Let's take our trie from earlier, and instead of writing it out using 5 bits per
character and 5 bits per index, we can instead Huffman code each position, as
well as the child counts themselves. 89.7% of our nodes have a length of three
or less, therefore Huffman coding acts to drastically cut down on how many bits
we need to encode our child counts as well!

Num Children | Huffman Code | Occurrences | %
-|-|-|-
1 | 1 | 6606 | 61.8%
2 | 01 | 2173 | 20.3%
3 | 000 | 821 | 7.7%
4 | 00111 | 348 | 3.3%
5 | 001101 | 175 | 1.6%

Writing the trie is then simply the same as writing the non-coded trie, but each
number of children and character is looked up in their respective Huffman tables
first.

Doing this gives rather fantastic results! 13,348 bytes uncompressed (15.7% of
baseline), and 13,299 Brotli encoded (90.4% of baseline). This is a nearly 10%
saving over-the-wire, and a nearly 85% saving uncompressed. This wins both
categories simultaneously! This is not overly surprising, in that we were able
to leverage the known structure of the data to implement similar methods to
Brotli encoding, but eek out extra drops of delicious compression.

| Attempt (Valid Words)          |  Lesson  | Uncompressed   | Compressed (Brotli) |
|---------                       | ------   | ------------   | ------------------- |
| Base                           | Preface  | 85,258         | 14,704              |
| Huffman Trie (Bitpacked, Smart)| Seven    | 13,348 (15.7%) | 13,299 (90.4%)      |

On all words (valid words + answers) the final size is 15,577 bytes Brotli
compressed vs. the original 21,020 bytes (74.1% of baseline). This is a nearly
27.5% reduction in over-the-wire size! This indicates that the encoding of new
words is extremely efficient, and we start to do much better than Brotli can
without leveraging known structure.

| Attempt (Valid+Answer Words)   |  Lesson  | Uncompressed   | Compressed (Brotli) |
|---------                       | ------   | ------------   | ------------------- |
| Base                           | Preface  | 103,779        | 21,020              |
| Huffman Trie (Bitpacked, Smart)| Seven    | 15,599 (15.0%) | 15,577 (74.1%)      |

Further, lookup time is not bad for the use-case in question (Wordle). With bit
offsets generated for each first letter, searches can be performed in <1ms on
average.

In the `clone` directory of this repository you will find a decoder implemented
in JavaScript which supports reading out a full word array, as well as doing
in-place searches for words. Offset generation can be performed explictly on
load (~20-35ms), or can be performed lazily as words are searched for. Explicit
generation is likely ideal for Wordle clones, as you want to avoid any jank on
submit to check if a word exists. That said, even on low-end hardware,
lazy-loaded searches shouldn't generate jank.

If you only care about over-the-wire benefits (which is probably all you should
care about) then you can read out the words to an array in memory. The
`includes` method in JavaScript is at least an order of magnitude faster on
lookups on a dictionary this size, despite being O(n). Words generally don't
share large prefixes due to their length, so most words can be rejected in just
a couple of char comparisons.

## Lesson 8: Tries Revisited

Another programmer, [Tab Atkins Jr.](https://gist.github.com/tabatkins) also
took a look at this problem and [used
tries](https://gist.github.com/tabatkins/c4b4e3c20d1b2663670d07b73f2623e8) to
compress the Wordle dictionary.

Here, Tab takes an alternate approach to how you can represent a trie. Instead
of tracking the character and its number of children, they instead use a
terminating separator which allows the decoder to know when to pop the stack.

Further, they don't do the tree to the full depth of five, but instead stop at
depth four and just list all two character suffixes. This acts to greatly reduce
the number of terminating characters needed, which is the biggest space-consumer
with this method.

In comparison to the representation in Lessons 4-8, it trades off needing to
track the size of each early node, with adding data to the end of every
terminating node.

Tab quotes compression numbers on his GitHub gist on the full all words
dictionary, so we've compared here similarly. He mentions that characters could
be packed in six bits, and the separators in four -- however, you can pack the
characters in five bits and the separator in four. The binary sequence `11110`
represents `30` and hence a decoder can pop whenever a sequence of `1111` is
found, or otherwise read one more bit to get the letter at that position.

Further, we can apply Huffman coding to the plain-text string instead, since we
have so many terminating characters, the code dedicates the fewest bits to it.
Finally, we can do per-position Huffman codes for each letter, artificially
inserting a lot of terminating characters into each input string so that the
Huffman code of each position accounts for terminating characters.

Brotli compressed, the Tab Atkins Jr approach is smaller than the Huffman Trie in
Lesson 7. This makes it optimal for bandwidth conservation purposes, but it ends
up being quite large in-memory. Attempting to bit-pack or Huffman encode it only
reduced what Brotli encoding could achieve, and as such they all performed worse
on bandwidth. They also all performed worse than the Huffman Trie when
uncompressed making them inferior (\*\*as a result, the numbers quoted below
don't even include the Huffman tables themselves as it wasn't worth the effort).

This makes the plain-text trie the best way to transmit the Wordle dictionary if
your server can leverage Brotli compression. It also greatly simplifies the
decoding process on the other end and there is no bitpacking or Huffman tables
to decode and leverage.

So why does this perform so well, and why doesn't Huffman coding compete? Brotli
compression utilizes more than just Huffman coding, it also uses [context
modelling](https://en.wikipedia.org/wiki/Context_model) and
[LZ77](https://en.wikipedia.org/wiki/LZ77_and_LZ78) compression. Put simply
it takes a content-independent approach, and attempts to pull commonly repeating
patterns from the text and represent them with a smaller representation. Think
of it like Huffman coding, but it analyzes the text to pick variable-length
n-grams and aims to optimize the set of n-grams that will produce the smallest
file.

One potential downside of this representation is that it makes it impossible to
pull a random word from the trie without decoding it completely, unless you also
know how many words are in the trie (at which point you can pick a random value
between 1 and N then seek, counting your total words until you hit N).

| Attempt  | Uncompressed   | Compressed (gzip) | Compressed (Brotli) |
|--------- | ------   | ------------   | ------------------- |
| tabatkins trie | 32,112 | 15,808 | 14,545
| tabatkins trie (Bitpacked) | 19,685 | 18,470 | 18,562 |
| tabatkins trie (Huffman)\*\* | 16,989 | 16,814 | 16,718 |
| tabatkins trie (Huffman, Positional)\*\* | 16,845 | 16,408 | 16,489 |

## Lesson 9: Variable Length Dictionaries

[hello wordl](https://hellowordl.net) is a Wordle clone that supports games
between 2 and 11 letters. Like Wordle they bundle their dictionary as part of
their JavaScript source, with the full uncompressed dictionary being well over
[2.5MB](https://github.com/lynn/hello-wordl/blob/main/src/dictionary.json).

Unlike Wordle, hello wordl uses gzip encoding, rather than Brotli which performs
quite a lot worse on text like this.

The Huffman trie outperforms both gzip and Brotli, with an uncompressed size of
353,615 bytes (13.09% of baseline), 341,817 bytes gzipped (68.26% of baseline)
and 341,292 bytes Brotli encoded (88.25%) of baseline. Here we see an 11.75%
reduction over if hello wordl opted to leverage Brotli encoding instead.

This highlights a weakness in being super overly specific in an encoding scheme.
Because we highly leveraged the specific-length nature of the Wordl
dictionaries, we don't have a way to easily leverage the high overlap of words
between words of different lengths.

Allowing variable lengths in our trie structure would require removing the
"smart" optimization, and instead using the length 0 children as a stop.
Further, we'd need to add one bit to every trie node to indicate whether the
current word terminates despite having children, otherwise we have no way to
decode "transport" if "transportation" is in the trie.

As a result, encoding the trie with variable length becomes bigger uncompressed
at 359,014 bytes. However, the extra bits add some structure that Brotli can
further add optimization to, bringing the Brotli compressed size to 295,713
bytes (with gzip being 317,268 bytes).

Ultimately, however, the independent tables are most likely to save the most
bandwidth and memory. Few users, if any, will play all 2-11 versions of hello
wordl in one session. As a result, sending the full dictionary for all 2-11 is a
waste. Therefore, it's likely optimal to send the dictionaries as-needed, or
bundling common ones together such as 2-6. The variable-length Huffman trie is
less than 50,000 bytes smaller than the fixed length ones combined. As such, if
the user doesn't play any one of N=8-11 that alone has saved more bandwidth than
having used the "more compressed" variable-length version.

| Attempt  | Uncompressed   | Compressed (gzip) | Compressed (Brotli) |
|--------- | ------   | ------------   | ------------------- |
Baseline | 2,700,926 | 500,752 | 386,721
Huffman Trie N=2 | 202 | 242 | 207
Huffman Trie N=3 | 1,024 | 1,064 | 1,029
Huffman Trie N=4 | 4,283 | 4,323 | 4,288
Huffman Trie N=5 | 15,597 | 15,618 | 15,578
Huffman Trie N=6 | 24,435 | 24,249 | 24,228
Huffman Trie N=7 | 44,344 | 43,329 | 43,314
Huffman Trie N=8 | 65,421 | 63,434 | 63,343
Huffman Trie N=9 | 75,094 | 72,500 | 72,253
Huffman Trie N=10 | 66,724 | 63,751 | 63,689
Huffman Trie N=11 | 56,491 | 53,307 | 53,363
Huffman Trie Total | 353,615 | 341,817 | 341,292
| | 13.09% | 68.26% | 88.25%
Variable Huffman Trie | 359,014 | 317,268 | 295,713
| | 13.29% | 63.36% | 76.47%

## Did We Succeed?

Yes.

The Super String method beat the Baseline in both compressed and uncompressed,
while also being very easy to work with, and having O(N) lookup time like the
original JSON. At minimum, it makes sense to just store your data like this,
it's easy to do and easy to work with. It's not the smallest, but it's actually
a good idea in practice.

Most of the other methods added complexity without really adding any benefit,
the uncompressed gains were good with bitpacked tries, but they generally made
over-the-wire more expensive and in the real world that's what costs you money.

The Huffman Coded Bitpacked Smart Trie achieves all of our goals handily,
achieving a 10%-25% over-the-wire saving, while also having a substantially
smaller memory footprint.

Overall, this is an interesting investigation into the various ways one can pack
data, and goes to show that modern techniques like Brotli are incredibly
effective and you need to have a lot of constraints on your data, and some
complex custom implementations if you want to hope to beat them.

## Results

| Attempt                        |  Lesson  | Uncompressed   | Compressed (Brotli) |
|---------                       | ------   | ------------   | ------------------- |
| Base                           | Preface  | 85,258         | 14,704              |
| Super String                   | One      | 53,286         | 14,639              |
| Protobuf String                | Two      | 53,289         | 14,639              |
| Bitpacked String               | Three    | 33,304         | 30,977              |
| Trie (JSON)                    | Four     | 170,785        | 17,070              |
| Trie (Protobuf)                | Four     | 82,642         | 19,196              |
| Trie (String)                  | Four     | 42,917         | 15,584              |
| Trie (String, Smart)           | Four     | 32,260         | 14,562              |
| Trie (Bitpacked)               | Five     | 26,692         | 14,092              |
| Trie (Bitpacked, Smart)        | Five     | 20,031         | 15,070              |
| 2-Gram Trie (Bitpacked)        | Six      | 29,997         | 17,357              |
| 2-Gram Trie (Bitpacked, Smart) | Six      | 19,340         | 17,067              |
| 3-Gram Trie (Bitpacked)        | Six      | 31,531         | 19,678              |
| 3-Gram Trie (Bitpacked, Smart) | Six      | 20,874         | 19,025              |
| 4-Gram Trie (Bitpacked)        | Six      | 40,062         | 21,210              |
| 4-Gram Trie (Bitpacked, Smart) | Six      | 25,408         | 22,484              |
| 5-Gram Trie (Bitpacked, Smart) | Six      | 31,971         | 18,204              |
| Huffman (Bitpacked)            | Seven    | 27,057         | 27,678              |
| Huffman Trie (Bitpacked, Smart)| Seven    | 13,348 (15.7%) | 13,299 (90.4%)      |

#### All Words

| Attempt                        |  Lesson  | Uncompressed   | Compressed (Brotli) |
|---------                       | ------   | ------------   | ------------------- |
| Base                           | Preface  | 103,779        | 21,020              |
| Huffman Trie (Bitpacked, Smart)| Seven    | 15,599 (15.0%) | 15,577 (74.1%)      |

| Attempt  | Uncompressed   | Compressed (gzip) | Compressed (Brotli) |
|--------- | ------   | ------------   | ------------------- |
| tabatkins trie | 32,112 | 15,808 | 14,545\*\*
| tabatkins trie (Bitpacked) | 19,685 | 18,470 | 18,562 |
| tabatkins trie (Huffman)\*\* | 16,989 | 16,814 | 16,718 |
| tabatkins trie (Huffman, Positional)\*\* | 16,845 | 16,408 | 16,489 |

#### HelloWordl Dictionary

| Attempt  | Uncompressed   | Compressed (gzip) | Compressed (Brotli) |
|--------- | ------   | ------------   | ------------------- |
Baseline | 2,700,926 | 500,752 | 386,721
Huffman Trie N=2 | 202 | 242 | 207
Huffman Trie N=3 | 1,024 | 1,064 | 1,029
Huffman Trie N=4 | 4,283 | 4,323 | 4,288
Huffman Trie N=5 | 15,597 | 15,618 | 15,578
Huffman Trie N=6 | 24,435 | 24,249 | 24,228
Huffman Trie N=7 | 44,344 | 43,329 | 43,314
Huffman Trie N=8 | 65,421 | 63,434 | 63,343
Huffman Trie N=9 | 75,094 | 72,500 | 72,253
Huffman Trie N=10 | 66,724 | 63,751 | 63,689
Huffman Trie N=11 | 56,491 | 53,307 | 53,363
Huffman Trie Total | 353,615 | 341,817 | 341,292
| | 13.09% | 68.26% | 88.25%
Variable Huffman Trie | 359,014 | 317,268 | 295,713
| | 13.29% | 63.36% | 76.47%
