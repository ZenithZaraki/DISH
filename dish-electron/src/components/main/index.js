
document.querySelector(".hamburger-button").onclick = () => {
    document.getElementById("dish-sidebar").classList.toggle("hidden");
};
document.querySelector(".wrench-button").onclick = () => {
    document.getElementById("dish-dialog").classList.toggle("hidden");
};

