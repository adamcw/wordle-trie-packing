class BitReader:
  def __init__(self, bit_array, char_map=None):
    self.bits = bit_array
    self.bin = self.bits.bin
    self.i = 0
    self.char_map = char_map

  def write(self, key, num_bits):
    bits = []
    val = self.char_map[key] if isinstance(key, str) else key
    mask = 0b1 << num_bits - 1
    for i in range(1, num_bits + 1):
      bits.append((val & mask) >> num_bits - i)
      mask >>= 1
    self.bits.append(bits)

  def append(self, data):
    self.bits.append(data)

  def read(self, num_bits):
    bits = self.bin[self.i:self.i+num_bits]
    self.i += num_bits
    return bits

  def read_int(self, num_bits):
    return int(self.read(num_bits), 2)

  def read_varint(self, table):
    buf = ''
    i = 0
    while True:
      buf += str(self.read(1))
      if buf in table.keys():
        return table[buf]
      i += 1

  def __len__(self):
    return len(self.bits)
