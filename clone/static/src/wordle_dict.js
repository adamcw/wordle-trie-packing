import { BitReader } from './bit_reader.js';

/*
 * Wordle Dictionary
 *
 * Operates on binary packed as a Huffman coded trie.
 *
 * Utilizes either explict or lazy generation of offsets into the binary in
 * order to speed up searches.
 *
 * Also supports expanding the data structure into an array of words, if no
 * in-memory advantages are desired.
 *
 */
class WordleDict {
  /*
   * Create a new WordleDict.
   *
   * Args:
   *  array_buffer:     The ArrayBuffer containing the binary data.
   *  generate_offsets: Pre-generate offsets for each letter in the dictionary,
   *                    this greatly speeds up average seek time at the cost of
   *                    init time.
   *  verbose:          Output console logs about the decoding process.
   */
  constructor(array_buffer, generate_offsets, verbose) {
    this.buf = array_buffer;
    this.bs = new BitReader(this.buf);
    this.tables = [];
    this._read_header(verbose)
    this._read_tables(verbose)
    this._i = this.bs.i;
    this._j = this.bs.j;
    this.offsets = {};
    if (generate_offsets === true) {
      this.generate_offsets();
    }
  }

  /*
   * Generate an array of all words in the dictionary.
   *
   * This parses the entire data structure into an array of strings, eliminating
   * any in-memory storage benefits of the data structure.
   */
  words() {
    this.bs.i = this._i;
    this.bs.j = this._j;
    const num_symbols = this.num_symbols;
    let words = [];
    for (let i = 0; i < num_symbols; ++i) {
      words = words.concat(this._read_payload(0, ''));
    }
    return words;
  }

  /*
   * Check if a word is in the dictionary.
   *
   * Utilizes known offsets to speed up search if they have been generated, or
   * if previous searches have been done to determine lazy-generated ones.
   */
  contains(word) {
    const first_letter = word[0];
    const idx = this._find_offset(first_letter);
    if (idx === null) {
      return this._search_payload(word, 0, '');
    }
    const num_symbols = this.num_symbols;
    for (let i = idx; i < num_symbols - idx; ++i) {
      // Cache offset for later searches.
      this.offsets[this.symbols[i]] = [this.bs.i, this.bs.j];
      if (this._search_payload(word, 0, '')) {
        return true;
      }

      // If we checked the branch that would contain this word and didn't find
      // it, we can stop searching.
      if (word.startsWith(this.symbols[i])) {
        break;
      }
    }
    return false;
  }

  /*
   * Generate all offsets to speed up searches.
   *
   * Can be done to prevent jank on user-interaction by performing the
   * generation at a more ideal time.
   */
  generate_offsets() {
    this.contains('zzzzzzzzzzzzzzzz')
  }

  word(index) {
    this.bs.i = this._i;
    this.bs.j = this._j;
    const num_symbols = this.num_symbols;
    let count = 0;
    for (let i = 0; i < num_symbols; ++i) {
      this.offsets[this.symbols[i]] = [this.bs.i, this.bs.j];
      count = this._specific_payload(index, count, 0, '');
      if (typeof count === "string") {
        return count;
      }
    }
    return false;
  }

  random_word(seed) {
    const num_symbols = this.num_symbols;
    const index = this._random(seed) % num_symbols;
    const first_letter = this.symbols[index];

    const idx = this._find_offset(first_letter);
    if (idx === null) {
      return this._random_payload(seed, 0, '');
    }

    for (let i = idx; i < num_symbols - idx; ++i) {
      this.offsets[this.symbols[i]] = [this.bs.i, this.bs.j];
      const word = this._random_payload(seed, 0, '');
      if (i === index) {
        return word;
      }
    }
    return false;
  }

  _find_offset(letter) {
    const num_offsets = Object.keys(this.offsets).length;
    if (num_offsets === 0) {
      return 0;
    }

    if (letter in this.offsets) {
      this.bs.i = this.offsets[letter][0];
      this.bs.j = this.offsets[letter][1];
      return null;
    }

    const idx = num_offsets - 1;
    this.bs.i = this.offsets[this.symbols[idx]][0];
    this.bs.j = this.offsets[this.symbols[idx]][1];
    return idx;
  }

  _random(a) {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0);
  }

  _read_header(verbose) {
    this.table_size = this.bs.read_int(8)
    this.word_size = this.bs.read_int(8)
    this.num_tables = this.bs.read_int(8)
    this.num_symbols = this.bs.read_int(16)
    this.table_depth = this.num_tables - 2;
    this.symbols = "abcdefghijklmnopqrstuvwxyz";

    if (verbose === true) {
      console.info("Table Size:", this.table_size);
      console.info("Word Size:", this.word_size);
      console.info("Num Tables:", this.num_tables);
      console.info("Num Symbols:", this.num_symbols);
    }
  }

  _read_tables(verbose) {
    const num_tables = this.num_tables;
    const table_size = this.table_size;
    const word_size  = this.word_size;
    for (let i = 0; i < num_tables; ++i) {
      const num_items = this.bs.read_int(table_size);
      if (verbose === true) {
        console.info("Table " + i + ":", num_items);
      }
      const table = {};
      for (let j = 0; j < num_items; ++j) {
        const symbol = this.bs.read_int(word_size);
        const encoding_size = this.bs.read_int(8)
        const encoding = this.bs.read(encoding_size);
        table[encoding] = symbol;
      }
      this.tables.push(table);
    }
    this.child_table = this.tables[this.table_depth + 1];
  }

  _read_payload(depth, prefix) {
    let num_children = 0;
    if (depth < this.table_depth) {
      num_children = this.bs.read_huff(this.child_table);
    }
    const symbol = this.bs.read_huff(this.tables[depth]);
    const decoded = this.symbols[symbol];
    if (depth == this.table_depth) {
      return [prefix + decoded];
    }
    let words = [];
    const new_depth = depth + 1;
    const new_prefix = prefix + decoded;
    for (let i = 0; i < num_children; ++i) {
      words = words.concat(this._read_payload(new_depth, new_prefix));
    }
    return words;
  }

  _search_payload(word, depth, prefix) {
    let num_children = 0;
    if (depth < this.table_depth) {
      num_children = this.bs.read_huff(this.child_table);
    }
    const symbol = this.bs.read_huff(this.tables[depth]);
    const decoded = this.symbols[symbol];
    if (depth == this.table_depth) {
      return prefix + decoded === word;
    }
    const new_depth = depth + 1;
    const new_prefix = prefix + decoded;
    for (let i = 0; i < num_children; ++i) {
      if (this._search_payload(word, new_depth, new_prefix)) {
        return true;
      }
    }
    return false;
  }

  _random_payload(seed, depth, prefix) {
    let num_children = 0;
    if (depth < this.table_depth) {
      num_children = this.bs.read_huff(this.child_table);
    }
    const symbol = this.bs.read_huff(this.tables[depth]);
    const decoded = this.symbols[symbol];
    if (depth == this.table_depth) {
      return prefix + decoded;
    }
    const new_depth = depth + 1;
    const new_prefix = prefix + decoded;
    const index = this._random(seed + depth + 1) % num_children;
    let words = [];
    for (let i = 0; i < num_children; ++i) {
      const word = this._random_payload(seed, new_depth, new_prefix);
      if (i === index) {
        words.push(word);
      }
    }
    return words;
  }

  _specific_payload(index, count, depth, prefix) {
    let num_children = 0;
    if (depth < this.table_depth) {
      num_children = this.bs.read_huff(this.child_table);
    }
    const symbol = this.bs.read_huff(this.tables[depth]);
    const decoded = this.symbols[symbol];
    if (depth == this.table_depth) {
      count++;
      if (count === index) {
        return prefix + decoded;
      }
      return count;
    }

    const new_depth = depth + 1;
    const new_prefix = prefix + decoded;
    for (let i = 0; i < num_children; ++i) {
      count = this._specific_payload(index, count, new_depth, new_prefix);
      if (typeof count === "string") {
        return count;
      }
    }
    return count;
  }
}

export { WordleDict };
