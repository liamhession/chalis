test( "map-initialization test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var lat = globalMarker.position.lat();
    var lng = globalMarker.position.lng();
    ok( lat == 81 && lng == -81, "Passed!" );
});

test( "predefined-location test", function() {
    var mapObj = loadMap(false, [81, -81]);
    mapObj.initialize();
    ok( map, "Passed!" );
});

test( "placeMarker-marker-existence test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var pos = new google.maps.LatLng(80, -80);
    mapObj.placeMarker(pos);
    ok( globalMarker, "Passed!" );
});

test( "placeMarker-marker-existence-with-correct-position test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var pos = new google.maps.LatLng(80, -80);
    mapObj.placeMarker(pos);
    var lat = globalMarker.position.lat();
    var lng = globalMarker.position.lng();
    ok( lat == 80 && lng == -80, "Passed!" );
});

test( "placeMarker-lat-lng-html test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var pos = new google.maps.LatLng(80, -80);
    mapObj.placeMarker(pos);
    var lat = $('#lat').html();
    var lng = $('#lng').html();
    ok( lat == 80 && lng == -80, "Passed!" );
});

test( "handleNoGeolocation-geoservice-failure test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var errorHandled = mapObj.handleNoGeolocation(true);
    ok( errorHandled === "Geolocation service failed.", "Passed!" );
});

test( "handleNoGeolocation-browser-failure test", function() {
    var mapObj = loadMap(false, [81, -81]);
    var errorHandled = mapObj.handleNoGeolocation(false);
    ok( errorHandled === "Browser does not support geolocation.", "Passed!" );
});
