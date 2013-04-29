$(document).ready(function() {
  function placeMarker(location) {
    var marker = new google.maps.Marker({
        position: location,
        map: map
    });

    globalMarker = marker;
    map.setCenter(location);
    $('#lat').html(location.lat());
    $('#lng').html(location.lng());
  }

  var map;
  var globalMarker = null;

  function initialize() {
    var mapOptions = {
      zoom: 18,
      mapTypeId: google.maps.MapTypeId.ROADMAP
    };
    map = new google.maps.Map(document.getElementById('map-canvas'),
        mapOptions);

    google.maps.event.addListener(map, 'click', function(event) {
      if (globalMarker) {
        globalMarker.setMap(null);
        globalMarker = null;
      }

      placeMarker(event.latLng);
    });

    // Try HTML5 geolocation
    if(navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(function(position) {
        var pos = new google.maps.LatLng(position.coords.latitude,
                                         position.coords.longitude);

        // var infowindow = new google.maps.InfoWindow({
        //   map: map,
        //   position: pos,
        //   content: 'Current position detected.'
        // });

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
      // Browser doesn't support Geolocation
      handleNoGeolocation(false);
    }
  }

  function handleNoGeolocation(errorFlag) {
    if (errorFlag) {
      var content = 'Error: The Geolocation service failed.';
    } else {
      var content = 'Error: Your browser doesn\'t support geolocation.';
    }

    var options = {
      map: map,
      position: new google.maps.LatLng(60, 105),
      content: content
    };

    var infowindow = new google.maps.InfoWindow(options);
    map.setCenter(options.position);
  }

  google.maps.event.addDomListener(window, 'load', initialize);
});