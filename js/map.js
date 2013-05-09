var globalMarker = null;
var map;

function loadMap(selectorMode, predefinedLoc) {
    this.placeMarker = function(location) {
        var marker = new google.maps.Marker({
                position: location,
                map: map
        });

        globalMarker = marker;
        map.setCenter(location);
        $('#lat').html(location.lat());
        $('#lng').html(location.lng());
    };

    this.initialize = function() {
        var mapOptions = {
            zoom: 18,
            mapTypeId: google.maps.MapTypeId.ROADMAP
        };
        map = new google.maps.Map(document.getElementById('map-canvas'),
                mapOptions);

        // enable click listener to place marker if in select location mode
        if (selectorMode) {
            google.maps.event.addListener(map, 'click', function(event) {
                if (globalMarker) {
                    globalMarker.setMap(null);
                    globalMarker = null;
                }

                placeMarker(event.latLng);
            });
        };

        // display predefined location if available
        if (predefinedLoc) {
            var pos = new google.maps.LatLng(predefinedLoc[0], predefinedLoc[1]);

            if (globalMarker) {
                globalMarker.setMap(null);
                globalMarker = null;
            }

            placeMarker(pos);
            $('#lat').html(pos.lat());
            $('#lng').html(pos.lng());

            map.setCenter(pos);
            return;
        }

        // access HTML5 geolocation
        if(navigator.geolocation) {
            // selectorMode or !predefinedLoc
            navigator.geolocation.getCurrentPosition(function(position) {
                var pos = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);

                if (globalMarker) {
                    globalMarker.setMap(null);
                    globalMarker = null;
                }
                placeMarker(pos);
                $('#lat').html(pos.lat());
                $('#lng').html(pos.lng());

                map.setCenter(pos);
            }, function() {
                handleNoGeolocation(true);
            });
        } else {
            // error
            handleNoGeolocation(false);
        }
    };

    this.handleNoGeolocation = function(errorFlag) {
        if (errorFlag) {
            var content = 'Geolocation service failed.';
        } else {
            var content = 'Browser does not support geolocation.';
        }

        var options = {
            map: map,
            position: new google.maps.LatLng(81, -81),
            content: content
        };

        map.setCenter(options.position);
        return content;
    };

    initialize();
    return this;
}