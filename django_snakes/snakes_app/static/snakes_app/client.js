var start_client = function start_client(width, height){
var WIDTH = width || 80;
var HEIGHT = height || 60;

var board = {snakes: [], apples: []};
var canvas = document.getElementById('canvas');
var c = canvas.getContext('2d');
var $leaderboard = $('#leaderboard');
var $error_log = $('#error_log');
var REFRESH_INTERVAL = 1000;

var repaint_needed = true;

function reloadBoard() {
    var reload_success = function(data){
        repaint_needed = true;
        board = data;
        setTimeout(reloadBoard, REFRESH_INTERVAL);
    };

    var reload_error = function(){
        setTimeout(reloadBoard, REFRESH_INTERVAL);
    };

    $.ajax({
        url: '/snakes_app/board/?KEY=' + KEY,
        success: reload_success,
        error: reload_error,
        dataType: 'json'
    });
}



function reloadLeaderboard() {
    var leader_success = function(data){
        repaint_needed = true;
        $leaderboard.html(data);
        setTimeout(reloadLeaderboard, 5000);
    };

    var leader_error = function(){
        setTimeout(reloadLeaderboard, 5000);
    };

    $.ajax({
        url: '/snakes_app/leaderboard/',
        success: leader_success,
        error: leader_error
    });
}


function reloadErrors() {
    if (KEY === null)
        return;

    var errors_success = function(data){
        repaint_needed = true;
        $error_log.html(data);
        setTimeout(reloadErrors, 5000);
    };

    var errors_error = function(){
        setTimeout(reloadErrors, 5000);
    };

    $.ajax({
        url: '/snakes_app/errors/' + KEY + '/',
        success: errors_success,
        error: errors_error
    });
}


function render() {
    c.clearRect(0, 0, WIDTH * 10, HEIGHT * 10);
    var i, j, snake, part, apple;
    for (i = 0; i < board.snakes.length; i++) {
        snake = board.snakes[i];
        c.fillStyle = snake.color;
        if(snake.current){
            c.strokeStyle = 'black';
        }else{
            c.strokeStyle = 'white';
        }

        if (snake.dead) {
            continue;
        }

        for (j = 0; j < snake.parts.length; j++) {
            part = snake.parts[j];
            c.fillRect(part[0] * 10, part[1] * 10, 9, 9);
            c.strokeRect(part[0] * 10, part[1] * 10, 9, 9);
        }
        part = snake.parts[snake.parts.length-1];
        c.fillStyle = '#000000';
        c.beginPath();
        c.arc(part[0] * 10 + 3, part[1] * 10 + 3, 1, 0, Math.PI*2);
        c.fill();
        c.beginPath();
        c.arc(part[0] * 10 + 7, part[1] * 10 + 3, 1, 0, Math.PI*2);
        c.fill();
        c.beginPath();
        c.arc(part[0] * 10 + 5, part[1] * 10 + 5, 3, Math.PI*0.2, Math.PI*(0.8));
        c.fill();
    }
    c.fillStyle = '#FF5555';
    for (i = 0; i < board.apples.length; i++) {
        apple = board.apples[i];
        c.beginPath();
        c.arc(apple[0] * 10 + 5, apple[1] * 10 + 5, 4, 0, Math.PI*2);
        c.fill();
    }
}

	reloadBoard();
	reloadLeaderboard();
	reloadErrors();
	var requestAnimFrame = window.requestAnimationFrame || mozRequestAnimationFrame;
	(function animloop() {
	    requestAnimFrame(animloop);
            if (repaint_needed) {
                render();
                repaint_needed = false;
            };
	}());

};
