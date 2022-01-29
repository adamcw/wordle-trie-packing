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

This also suggests a reason Protobufs prefer to remain byte-aligned with their
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

### Trie Protobuf

Protobufs offer reasonable packing of integers, and can represent nested data
fairly efficiently as well. Converting the trie to Protobuf results in an
uncompressed size of 82,642 bytes and a Brotli compressed size of 19,196 bytes.

Uncompressed this is marginally better than baseline, but it compresses worse,
and performs worse than substantially easier-to-work-with solutions such as a
basic Super String from Lesson 1.

### Trie String

We know that strings seem to compress much better than bitpacked/binary data, so
what if we just represented the trie in a plaintext format. At this point we
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

## Did We Succeed?

Yes, but not in the expected way.

The Super String method beat the Baseline in both compressed and uncompressed,
while also being very easy to work with, and having O(N) lookup time like the
original JSON. At minimum, it makes sense to just store your data like this,
it's easy to do and easy to work with. It's not the smallest, but it's actually
a good idea in practice.

If you actually want a trie, and plan to expand it into memory, the "Smart"
string-based trie was marginally smaller in both uncompressed and compressed
cases over a simple Super String. This could have some use if you didn't care
about lookup time, or would lazy-load the data into a regular trie while
parsing.

The bitpacked trie is incredibly small but throws away all convenience. Lookups
are horrendously slow, your letters are integers now, and you have to
manually read out this horrible file format in chunks of five bits which makes
neither you, your code, or your computer happy.

## Results

| Attempt                        |  Lesson  | Uncompressed | Compressed (Brotli) |
|---------                       | ------   | ------------ | ------------------- |
| Base                           | Preface  | 85,258       | 14,704              |
| Super String                   | One      | 53,286       | 14,639              |
| Protobuf String                | Two      | 53,289       | 14,639              |
| Bitpacked String               | Three    | 33,304       | 30,977              |
| Trie (JSON)                    | Four     | 170,785      | 17,070              |
| Trie (Protobuf)                | Four     | 82,642       | 19,196              |
| Trie (String)                  | Four     | 42,917       | 15,584              |
| Trie (String, Smart)           | Four     | 32,260       | 14,562              |
| Trie (Bitpacked)               | Five     | 26,692       | 14,092*             |
| Trie (Bitpacked, Smart)        | Five     | 20,031       | 15,070              |
| 2-Gram Trie (Bitpacked)        | Six      | 29,997       | 17,357              |
| 2-Gram Trie (Bitpacked, Smart) | Six      | 19,340*      | 17,067              |
| 3-Gram Trie (Bitpacked)        | Six      | 31,531       | 19,678              |
| 3-Gram Trie (Bitpacked, Smart) | Six      | 20,874       | 19,025              |
| 4-Gram Trie (Bitpacked)        | Six      | 40,062       | 21,210              |
| 4-Gram Trie (Bitpacked, Smart) | Six      | 25,408       | 22,484              |
| 5-Gram Trie (Bitpacked, Smart) | Six      | 31,971       | 18,204              |
