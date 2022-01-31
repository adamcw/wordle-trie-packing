import { WordleDict } from './wordle_dict.js';

function today_offset() {
  const start_date = new Date(2021, 5, 19, 0, 0, 0, 0);
  const time_delta = new Date().setHours(0, 0, 0, 0) - start_date.setHours(0, 0, 0, 0);
  return Math.round(time_delta / 86400000)
}

async function get_answers() {
  return fetch('./static/answers.bin')
    .then(res => res.arrayBuffer())
    .then(data => {
      const view = new DataView(data);
      const day_offset = view.getUint16(0, false);
      const day_count = view.getUint8(2, false);
      let offsets = [];
      for (let i = 0; i < day_count; ++i) {
        offsets.push(view.getUint16(3+(i*2), false));
      }
      return [day_offset, day_count, offsets];
    });
}

async function get_words() {
  return fetch('./static/words.bin')
    .then(res => res.arrayBuffer())
}


async function main() {
  const words = await get_words();
  const res = await get_answers();

  let s = performance.now();
  const dict = new WordleDict(
    words,
    false,  // generate_offsets.
    false  // verbose.
  );
  let time_taken = (performance.now() - s).toFixed(2);
  console.log(`Loaded in ${time_taken}ms`);

  const day_offset = res[0];
  const answers = res[2];
  const base_offset = today_offset();
  const answer_offset = base_offset - day_offset;
  const offset = answers[answer_offset];
  s = performance.now();
  let word = dict.word(offset);
  time_taken = (performance.now() - s).toFixed(2);
  console.log(`Found today's word ${word} in ${time_taken}ms`);

  for (let i = 0; i < 5; ++i) {
    s = performance.now();
    let word = dict.random_word(i);
    time_taken = (performance.now() - s).toFixed(2);
    console.log(`Random ${word} in ${time_taken}ms`);
  }

  s = performance.now();
  const all_words = dict.words();
  time_taken = (performance.now() - s).toFixed(2);
  console.log(all_words);
  console.log(`Words generated in ${time_taken}ms`);

  for (let word of ["aahed", "rosti", "zymic", "aaaaa", "zzzzz"]) {
    s = performance.now();
    let contains = dict.contains(word) ? "found" : "absent";
    time_taken = (performance.now() - s).toFixed(2);
    console.log(`Word ${word} ${contains} in ${time_taken}ms`);
  }
}

main();
