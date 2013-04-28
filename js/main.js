// TODO: please template this variable if available
// var challenge_name = {{ challenge_name }};

$(document).ready(function(){
    
    // click handler for the submit button
    $('#new-challenge-short').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/new',
            type: 'POST',
            data: {'description': $('#short-desc').val()}
        });
    });

    // click handler for the submit button
    // TODO: I am now passing 'prize' as a string array. Haven't implement tabbed text area yet. Only passing first prize desc.
    $('#new-challenge-detailed').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/edit',
            type: 'POST',
            data: {'objective': $('#objective').val(),
                   'period': [$('#time-unit').val(), $('#time-length').val(), '' + $('#year').val() + $('#month').val() + $('#day').val()],
                   'prize': [$('#prize-desc').html(), '', '', '']}
        });
    });

    // click handler for the submit button
    $('#add-invitee').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/send-invite',
            type: 'POST',
            data: {'email': $('#invitee-email').val()}
        });
    });

});