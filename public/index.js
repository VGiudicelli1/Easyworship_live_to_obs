const sio = io();

const div_sizing = document.querySelector("div.sizing");
const div_content = document.querySelector("div.content");

sio.on("disconnect", () => {
    setText("");
});

sio.on("data", (data) => {
    setText(data);
});

function isOverflown(element) {
  return element.scrollHeight > element.clientHeight || element.scrollWidth > element.clientWidth;
}

function setText(text) {
    // init dichotomie
    let max_font_size = 1;
    let min_font_size = 0;
    div_content.style.display = text == "" ? "None" : "";
    div_sizing.innerText = text;

    // start dichotomie loop
    for (let _i = 0; _i < 10; _i++) {
        const mean_font_size = (max_font_size + min_font_size) / 2;
        div_sizing.style.fontSize = mean_font_size + "em";
        if (isOverflown(div_sizing)) {
            max_font_size = mean_font_size;
        } else {
            min_font_size = mean_font_size;
        }
    }

    // use dichotomie result
    div_content.style.fontSize = min_font_size + "em";
    div_content.innerText = text;
}