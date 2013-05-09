// TODO: please template this variable if available
// var challenge_name = {{ challenge_name }};

$(document).ready(function(){

    /******** Initializations ******/

    //////////////// Home page ///////////////////////
    // Fill in default text when top chanllenges are not populated yet
    $('.top-challenge td').each(function() {
        if ($(this).html() === '') {
            $(this).html('no chanllenge yet');
        };
    });


    /*********** Handlers **********/

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

        // Unhide the objective action box if the objective is now highest occurrence type
        if (objectiveType == "Highest Occurrence") {
            $('#objective-name-block').removeClass('hidden');
            $('.geo-objective-details').addClass('hidden');
        }
        // Unhide and hide appropriately for change to geolocation objective
        else if (objectiveType == "Location Visits") {
            $('.geo-objective-details').removeClass('hidden');
            $('#objective-name-block').addClass('hidden');
            loadMap(true);
        }   
        // Hide both extra infos if not selecting either of above objective types
        else {
            $('.geo-objective-details').addClass('hidden');
            $('#objective-name-block').addClass('hidden');
        }
    });


    // When the prize/punishment slot changes, change which description box shows
    $('#dk_container_place-selector .dk_options_inner a').click(function() {
        var place = $(this).html();
        var placeId = '#first-desc';
        if (place == "Second") {
            placeId = '#second-desc';
        }
        else if (place == "Second to Last") {
            placeId = '#second-to-last-desc';
        }
        else if (place == "Last") {
            placeId = '#last-desc';
        }

        // Remove hidden class from corresponding box's parent
        var parentDiv = $(placeId).parent();
        parentDiv.removeClass('hidden');

        // Hide all that parent's siblings
        parentDiv.siblings().addClass('hidden');        
    });

    // Click handler for the "Save Changes" button
    $('#challenge-updated').click(function(evt){
        evt.preventDefault();

        // Create a data module that contains all the essential, add to it based on objective
        var data = {'objective': $('#objective').val(),
                   'unit': $('#time-unit').val(),
                   'length': $('#time-length').val(),
                   'year': $('#year').val(),
                   'month': $('#month').val(),
                   'day': $('#day').val(),
                   'stakes1': $('#first-desc').val(),
                   'stakes2': $('#second-desc').val(),
                   'stakes3': $('#second-to-last-desc').val(),
                   'stakes4': $('#last-desc').val()               
                   };                
        if ($('#objective').val() == "highest-occurrence") {
            data['objective-name'] = $('#objective-name').val();
        }
        else if ($('#objective').val() == "location") {
            // Check if location info is ready
            var lat = $('#lat').html();
            var lng = $('#lng').html();
            if (lat === "Loading geoinfo..." || lng === "Loading geoinfo...") {
                alert("Please choose a location.");
                return;
            }

            // Grab data from #geo-objective-details
            data['checkin-loc'] = lat + ', ' + lng;
            data['radius'] = $('#radius').val();
            data['checkin-loc-name'] = $('#loc_name').val();
        }

        $.ajax({
            url: 'edit',
            type: 'POST',
            data: data
        });
    });

    // Click handler for the "Edit" button
    $('#edit-challenge').click(function(evt){
        evt.preventDefault();
        window.location.replace('./details?new=1');
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
        var radius = $('#radius').html();
        var lat = $('#lat').html();
        var lng = $('#lng').html();
        if (lat === "Loading geoinfo..." || lng === "Loading geoinfo...") {
            alert("Your location hasn't been detected yet.\nPlease checkin later.");
            return;
        }
        var loc = $('#location').html().split(',', 2);
        var locLat = loc[0];
        var locLng = loc[1];
        var locObj = new google.maps.LatLng(locLat, locLng);
        var checkinObj = new google.maps.LatLng(lat, lng);
        var distance = google.maps.geometry.spherical.computeDistanceBetween(locObj, checkinObj, 3956.6);
        if (distance > radius) {
            $('#geo-checkin').html("Sorry, you are not within the valid checkin range.");
            return;
        }


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

        // Return if user does not provide valid gmail account
        var emailAddr = $('#invitee-email').val();
        var lowerCased = emailAddr.toLowerCase();

        if (!(/^([A-Za-z0-9_\-\.])+\@(gmail)\.(com)$/.test(lowerCased))) {
            alert('Oops, invalid Gmail account.\n' +
                'Accounts can only be like "example@gmail.com" at this time.');
            return;
        }

        // Send invitation if account is valid
        $.ajax({
            url: 'send-invite',
            type: 'POST',
            data: {'email': emailAddr}
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
