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

});