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

  read_int(num_bits, buffer, data_view) {
    const buf = buffer || new ArrayBuffer(Math.ceil(num_bits / 8.));
    const view = data_view || new DataView(buf);
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

export { BitReader }
