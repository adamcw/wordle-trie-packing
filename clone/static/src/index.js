(function(window) {

/*
 * Bit Reader.
 *
 * Allows for reading an ArrayBuffer as a stream of bits.
 */
class BitReader {
  constructor(array_buffer) {
    this.buf = new Int8Array(array_buffer);
    this.i = 0;
    this.j = 0;
  }

  /*
   * Read the current position and increment the counters.
   */
  read_bit() {
    const bit = (this.buf[this.i] & (128 >> this.j)) >> (7-this.j);
    if (this.j === 7) {
      this.j = 0;
      this.i++;
    } else {
      this.j++;
    }
    return bit;
  }

  read(num_bits) {
    let buf = '';
    const end = num_bits - 1;
    for (let i = 0; i <= end; ++i) {
      buf += this.read_bit();
    }
    return buf
  }

  read_int(num_bits) {
    const buf = new ArrayBuffer(Math.ceil(num_bits / 8.));
    const view = new DataView(buf);
    const end = num_bits - 1;
    let offset = 0;
    let value = 0;
    for (let i = 0; i <= end; ++i) {
      value |= this.read_bit() << end - i;
      const new_offset = Math.floor(i / num_bits)
      if (new_offset != offset) {
        view.setInt8(offset, value, true);
        value = 0;
        offset = new_offset;
      }
    }
    view.setInt8(offset, value, true);

    if (num_bits <= 8) {
      return value;
    } else if (num_bits <= 16) {
      return view.getInt16(0, true);
    } else if (num_bits <= 32) {
      return view.getInt32(0, true);
    } else if (num_bits <= 64) {
      return view.getInt64(0, true);
    } else {
      throw 'Cannot read_int for more than 64 bits.'
    }
  }

  read_huff(table) {
    let buf = '';
    for (let i = 0;; ++i) {
      buf += this.read_bit()
      if (buf in table) {
        return table[buf];
      }
    }
  }
}


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
    if (first_letter in this.offsets) {
      this.bs.i = this.offsets[first_letter][0];
      this.bs.j = this.offsets[first_letter][1];
      return this._search_payload(word, 0, '');
    }

    this.bs.i = this._i;
    this.bs.j = this._j;
    const num_symbols = this.num_symbols;

    for (let i = 0; i < num_symbols; ++i) {
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
}

fetch('./static/words.bin')
  .then(res => res.arrayBuffer())
  .then(data => {
    let s = performance.now();
    const dict = new WordleDict(
      data,
      true,  // generate_offsets.
      false  // verbose.
    );
    time_taken = (performance.now() - s).toFixed(2);
    console.log(`Loaded in ${time_taken}ms`);

    s = performance.now();
    const words = dict.words();
    time_taken = (performance.now() - s).toFixed(2);
    console.log(words);
    console.log(`Words generated in ${time_taken}ms`);

    for (let word of ["aahed", "rosti", "zymic", "aaaaa", "zzzzz"]) {
      s = performance.now();
      let contains = dict.contains(word) ? "found" : "absent";
      time_taken = (performance.now() - s).toFixed(2);
      console.log(`Word ${word} ${contains} in ${time_taken}ms`);
    }
  });

})(window);
