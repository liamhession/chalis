// TODO: please template this variable if available
// var challenge_name = {{ challenge_name }};

$(document).ready(function(){

    //////////////// Home page ///////////////////////
    // Handle a click on any of the top-challenge list elements on the home page
    //  will create a new challenge with the given description and the current user in it
    $('.top-challenge').click(function() {
        var description = $(this).find('td').html();
        
        // Put the clicked-on description in the hidden form element, then submit form
        $('#short-desc').val(description);
    });

    //////////////// Details page ///////////////////////
    // When the challenge type changes, either make the objective name field dis- or appear
    $('#dk_container_objective .dk_options_inner a').click(function() { 
        var objectiveType = $(this).html();
        if (objectiveType == "Highest Occurrence") {
            $('#objective-type-block').after('<div class="span3 offset2" id="objective-name-block"> \
                Objective Name \
                <input type="text" id="objective-name" placeholder="Action that comprises checkin"> \
                </div>');
        }
        else {
            $('#objective-name-block').remove();
        }   
    });

    // Click handler for the "Save Changes" button
    // TODO: I am now passing 'prize' as a string array. Haven't implement tabbed text area yet.
    $('#challenge-updated').click(function(evt){
        evt.preventDefault();

        // Create a data module that contains all the essential, add to it based on objective
        var data = {'objective': $('#objective').val(),
                   'unit': $('#time-unit').val(),
                   'length': $('#time-length').val(),
                   'year': $('#year').val(),
                   'month': $('#month').val(),
                   'day': $('#day').val()
                   };                
        if ($('#objective').val() == "highest-occurrence") {
            data['objective-name'] = $('#objective-name').val();
        }
        else if ($('#objective').val() == "location") {
            data['checkin-loc'] = "23.44, -21.04";
            data['radius'] = 200;
            data['checkin-loc-name'] = "Cravings";
        }

        $.ajax({
            url: 'edit',
            type: 'POST',
            data: data
        });
    });


    //////////////// Checkin page ///////////////////////
    // On the attempt to submit a check-in on a geolocation challenge page,
    //  the proximity to the location is checked, as well as last checkin time
    $('#geo-checkin').click(function(){
        var canCheckin = true;
        // Check that they didn't check in at this location fewer than 2 hrs ago
        var lastCheckinTimestamp = $('#last-checkin').html();
        if (lastCheckinTimestamp != "") {
            // Get time-stamp of the current moment, GMT to compare to last checkin
            var currTimestamp = Math.floor((new Date()).getTime() / 1000);
            var secsIn2Hrs = 2*60*60;
            canCheckin = (currTimestamp - lastCheckinTimestamp) > secsIn2Hrs;
        }
        
        // If they can't check in at this point notify them they're trying too often
        if (!canCheckin) {
            var minsTillNext = Math.floor((secsIn2Hrs - (currTimestamp - lastCheckinTimestamp))/60);
            $('#geo-checkin').html("Wait "+minsTillNext+" min to checkin again");
            return;
        }

        // Check that they are actually within the correct radius of the location


        // If they can't check in at this point, notify them they're not in the radius
        if (!canCheckin) {
            $('#geo-checkin').html("You are not within range");
            return;
        }

        // Send ajax post to the do-checkin page
        $.ajax({
            url: 'do-checkin',
            type: 'POST',
            data: {'objective_id': $('#geo-id').html()},
            success: function() { $('#geo-checkin').html("You checked in!"); }
        });
    });

    // General objective checkin page just limits repeated checkins less than 1 min apart
    $('#gen-checkin').click(function() {
        var canCheckin = true;
        var lastCheckinTimestamp = $('#last-checkin').html();
        if (lastCheckinTimestamp != "") {
            // Get time-stamp of the current moment, GMT to compare to last checkin
            var currTimestamp = Math.floor((new Date()).getTime() / 1000);
            var secsIn1Min = 60;
            canCheckin = (currTimestamp - lastCheckinTimestamp) > secsIn1Min;
        }

        // If they can't check in at this point notify them they're trying too often        
        if (!canCheckin) {
            $('#gen-checkin').html("Wait a minute to check in");
            return;
        }

        // Send ajax post to the do-checkin page
        $.ajax({
            url: 'do-checkin',
            type: 'POST',
            data: {'objective_id': $('#gen-id').html()},
            success: function() { $('#gen-checkin').html("You checked in!"); }
        });
    });

    //////////////// Invite page ///////////////////////
    // click handler for the submit button on challengers.html
    $('#add-invitee').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: 'send-invite',
            type: 'POST',
            data: {'email': $('#invitee-email').val()}
        });

        // Clear the email box
        $('#invitee-email').val("");
    });


    //////////////// Join page ///////////////////////
    // click handler for the submit button on reddit-join.html
    $('#reddit-submit').click(function(evt){
        evt.preventDefault();
        $.ajax({
            url: 'join',
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
