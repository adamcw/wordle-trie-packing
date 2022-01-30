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
and one with answers. There are 2,315 answers and 10,657 valid dictionary words.
The answers have been omitted from this repository 1) to at least pretend to
protect the integrity of the game 2) it's not that wise to send ~6 years worth
of answers with every request when only one is needed anyway.

The valid dictionary words take up 85,258 bytes uncompressed, or ~48% of the
total source size. Compressed on its own with Brotli encoding, this becomes
14,704 bytes.

However, if you remove the valid dictionary words, and Brotli
compress the source it drops to 33,430 bytes. This would represent that the
"cost" of the extra valid dictionary words is 6,482 bytes. This
encoding is sort of cheated, as mentioned sending the full answers dictionary
doesn't make much sense if we're size conscious, and the answers dictionary
makes compressing the valid words dictionary much easier.

Removing both dictionaries from the source and Brotli compressing it, results in
only 18,461 bytes (46% of compressed size). This means even with high
compression, these dictionaries alone account for half the bandwidth.

## Problem Statement

How small can we represent the valid dictionary words, and can we beat Brotli
compression by attempting to make a custom file format that leverages the very
specific nature of the Wordle dictionary.

## Lesson 1: JSON is Big

All words in Wordle are the same length. This means that you can store them in
one large contiguous string. Further, all characters are lowercase and only
between [a-z]. You can simply iterate this large string jumping n-characters
(five in the original Wordle) to find if a word is in the dictionary.

We can therefore remove the square brackets, quotation marks and commas that
make up the JSON string.

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
integer with at least eight bits, this is the same size as a char. The extra
three bytes will be the header for the protobuf.

This means, if we want to do better uncompressed, we need to do better than 8
bits per character. If we want to do better compressed, we're going to have to
come up with a more compact encoding scheme than the general approach taken by
Brotli.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Super String                   | 53,286       | 14,639              |
| Protobuf String                | 53,289       | 14,639              |

## Lesson 3: Bit-Packing

The numbers 0-26 and be represented with only five bits, rather than eight, a
37.5% size reduction. If we convert each character to a number, then pack these
into a binary format this way, we can get a notable uncompressed size saving.

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
compression algorithms on the wire.

| Attempt                        | Uncompressed | Compressed (Brotli) |
|---------                       | ------------ | ------------------- |
| Base                           | 85,258       | 14,704              |
| Super String                   | 53,286       | 14,639              |
| Protobuf String                | 53,289       | 14,639              |
| Bitpacked String               | 33,304       | 30,977              |

## Lesson 4: Tries

A Trie is essentially a prefix-tree. That is, you can encode the words MOUNT and
MOUTH as the following tree:

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
17,070 bytes Brotli encoded. Uncompressed it is more than tw:w
ice as big as the
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
1M1O2U1T0H1N1T
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

Further, lookup time is not bad for the use-case in question (Wordle), with an
unoptimized decoding method in Python taking ~0.065s to decode the entire
contents into an array containing all of the words. A simple check for whether a
word is in the array could be done much faster on average.

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
achieving a 10% over-the-wire saving, while also having a substantially smaller
memory footprint.

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
