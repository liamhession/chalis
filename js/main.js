// TODO: please template this variable if available
// var challenge_name = {{ challenge_name }};

$(document).ready(function(){
    
    /* This shouldnt be asynch. Its a post from a form
		// click handler for the submit button on frontpage.html
    $('#new-challenge-short').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/new',
            type: 'POST',
            data: {'description': $('#short-desc').val()}
        });
    });
		*/
		
    // click handler for the submit button on details.html
    // TODO: I am now passing 'prize' as a string array. Haven't implement tabbed text area yet.
    $('#new-challenge-detailed').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/edit',
            type: 'POST',
            data: {'objective': $('#objective').val(),
                   'period': [$('#time-unit').val(), $('#time-length').val(), '' + $('#year').val() + $('#month').val() + $('#day').val()],
                   'prize': [$('#first-desc').html(), $('#second-desc').html(), $('#snd2last-desc').html(), $('#last-desc').html()]}
        });
    });

    // click handler for the submit button on challengers.html
    $('#add-invitee').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/send-invite',
            type: 'POST',
            data: {'email': $('#invitee-email').val()}
        });
    });

    // click handler for the submit button on reddit-join.html
    $('#reddit-submit').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/join',
            type: 'POST',
            data: {'relevant_logins': $('#reddit-user').val()}
        });
    });

    // click handler for the submit button on gen-join.html
    $('#gen-accept').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/join',
            type: 'POST',
            data: {'gen_join': true}
        });
    });

    // click handler for the submit button on geo-join.html
    $('#geo-accept').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: '/' + challenge_name + '/join',
            type: 'POST',
            data: {'geo_join': true}
        });
    });

});