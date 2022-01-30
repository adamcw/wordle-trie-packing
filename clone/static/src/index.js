import { WordleDict } from './wordle_dict.js';

fetch('./static/words.bin')
  .then(res => res.arrayBuffer())
  .then(data => {
    let s = performance.now();
    const dict = new WordleDict(
      data,
      true,  // generate_offsets.
      false  // verbose.
    );
    let time_taken = (performance.now() - s).toFixed(2);
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
