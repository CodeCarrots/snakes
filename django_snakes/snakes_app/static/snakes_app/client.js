var WIDTH = 80;
var HEIGHT = 60;

var board = {snakes: [], apples: []};
var canvas = document.getElementById('canvas');
var c = canvas.getContext('2d');
var $leaderboard = $('#leaderboard');
var $error_log = $('#error_log');
var REFRESH_INTERVAL = 1000;

function reloadBoard() {
    var reload_success = function(data){
        board = data;
        setTimeout(reloadBoard, REFRESH_INTERVAL);
    };

    var reload_error = function(){
        setTimeout(reloadBoard, REFRESH_INTERVAL);
    };

    $.ajax({
        url: '/snakes_app/board/',
        success: reload_success,
        error: reload_error,
        dataType: 'json'
    });
}

reloadBoard();


function reloadLeaderboard() {
    var leader_success = function(data){
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
reloadLeaderboard();


function reloadErrors() {
    if (KEY === null)
        return;

    var errors_success = function(data){
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
reloadErrors();


function render() {
    c.clearRect(0, 0, WIDTH * 10, HEIGHT * 10);
    var i, j, snake, part, apple;
    for (i = 0; i < board.snakes.length; i++) {
        snake = board.snakes[i];
        c.fillStyle = snake.color;

        if (snake.dead) {
            continue;
        }

        for (j = 0; j < snake.parts.length; j++) {
            part = snake.parts[j];
            c.fillRect(part[0] * 10, part[1] * 10, 9, 9);
        }
    }
    c.fillStyle = '#FF0000';
    for (i = 0; i < board.apples.length; i++) {
        apple = board.apples[i];
        c.beginPath();
        c.arc(apple[0] * 10 + 5, apple[1] * 10 + 5, 4, 0, Math.PI*2);
        c.fill();
//        c.fillRect(apple[0] * 10, apple[1] * 10, 10, 10);
    }
}

var requestAnimFrame = window.requestAnimationFrame || mozRequestAnimationFrame;
(function animloop() {
    requestAnimFrame(animloop);
    render();
}());
