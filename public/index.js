const sio = io();

const div = document.querySelector("div");

sio.on("disconnect", () => {
    div.innerText = "";
});

sio.on("data", (data) => {
    div.innerText = data;
});