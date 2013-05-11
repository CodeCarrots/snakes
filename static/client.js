var WIDTH = 80;
var HEIGHT = 60;

var board = {snakes: [], apples: []};
var canvas = document.getElementById('canvas');
var c = canvas.getContext('2d');


function reloadBoard() {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
	if (xhr.readyState === 4 && xhr.status === 200) {
            board = JSON.parse(xhr.responseText);
	}
    }
    xhr.open('GET', '/board', true);
    xhr.send();
    setTimeout(reloadBoard, 1000);
}

reloadBoard();


function render() {
    c.clearRect(0, 0, WIDTH * 10, HEIGHT * 10);
    var i, j, snake, part, apple;
    c.fillStyle = '#000000';
    for (i = 0; i < board.snakes.length; i++) {
        snake = board.snakes[i];
        if (snake.dead) {
            continue;
        }

        for (j = 0; j < snake.parts.length; j++) {
            part = snake.parts[j];
            c.fillRect(part[0] * 10, part[1] * 10, 10, 10);
        }
    }
    c.fillStyle = '#FF0000';
    for (i = 0; i < board.apples.length; i++) {
        apple = board.apples[i];
        c.fillRect(apple[0] * 10, apple[1] * 10, 10, 10);
    }
}

var requestAnimFrame = window.requestAnimationFrame || mozRequestAnimationFrame;
(function animloop(){
    requestAnimFrame(animloop);
    render();
}());
