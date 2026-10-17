import { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  PhoneCall,
  Navigation,
  MapPin,
  AlertTriangle,
  Hospital,
  Activity,
  Search,
  Crosshair,
  ShieldAlert,
} from 'lucide-react';

// Custom Leaflet marker icons using standard inline SVG data URIs
const createIcon = (color) =>
  L.divIcon({
    className: 'custom-div-icon',
    html: `<div style="background-color: ${color}; width: 26px; height: 26px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; color: white; font-size: 13px; font-weight: bold;">+</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -14],
  });

const hospitalIcon = createIcon('#dc2626'); // red
const clinicIcon = createIcon('#059669'); // emerald
const userIcon = L.divIcon({
  className: 'user-location-pin',
  html: `<div style="background-color: #2563eb; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 0 10px #2563eb;"></div>`,
  iconSize: [20, 20],
  iconAnchor: [10, 10],
});

// Predefined fallback healthcare centers for key Indian cities (if Overpass is offline/timeout)
const PRESET_CITIES = {
  Bhubaneswar: {
    lat: 20.2961,
    lon: 85.8245,
    state: 'Odisha',
    centers: [
      { name: 'AIIMS Bhubaneswar', type: 'hospital', lat: 20.2312, lon: 85.7891, address: 'Sijua, Patrapada, Bhubaneswar', phone: '0674-2476789' },
      { name: 'Capital Hospital Bhubaneswar', type: 'hospital', lat: 20.2644, lon: 85.8282, address: 'Unit 6, Ganga Nagar, Bhubaneswar', phone: '0674-2391983' },
      { name: 'SCB Medical College & Hospital', type: 'hospital', lat: 20.4786, lon: 85.8828, address: 'Mangalabag, Cuttack', phone: '0671-2414080' },
      { name: 'District Skin & Leprosy Clinic', type: 'clinic', lat: 20.2721, lon: 85.8335, address: 'Bapuji Nagar, Bhubaneswar', phone: '0674-2530111' },
    ],
  },
  'New Delhi': {
    lat: 28.6139,
    lon: 77.209,
    state: 'Delhi',
    centers: [
      { name: 'AIIMS New Delhi (Dermatology Dept)', type: 'hospital', lat: 28.5672, lon: 77.21, address: 'Sri Aurobindo Marg, Ansari Nagar, New Delhi', phone: '011-26588500' },
      { name: 'Safdarjung Hospital', type: 'hospital', lat: 28.5694, lon: 77.2078, address: 'Ring Road, New Delhi', phone: '011-26165060' },
      { name: 'Dr. Ram Manohar Lohia Hospital', type: 'hospital', lat: 28.6247, lon: 77.2024, address: 'Baba Kharak Singh Marg, New Delhi', phone: '011-23365525' },
    ],
  },
  Mumbai: {
    lat: 19.076,
    lon: 72.8777,
    state: 'Maharashtra',
    centers: [
      { name: 'KEM Hospital & Seth GS Medical College', type: 'hospital', lat: 19.0028, lon: 72.8427, address: 'Acharya Donde Marg, Parel, Mumbai', phone: '022-24107000' },
      { name: 'Lokmanya Tilak Municipal General Hospital (Sion)', type: 'hospital', lat: 19.0372, lon: 72.8598, address: 'Sion West, Mumbai', phone: '022-24076381' },
      { name: 'Sir JJ Hospital', type: 'hospital', lat: 18.9632, lon: 72.8339, address: 'Byculla, Mumbai', phone: '022-23735555' },
    ],
  },
  Bengaluru: {
    lat: 12.9716,
    lon: 77.5946,
    state: 'Karnataka',
    centers: [
      { name: 'Victoria Hospital (Bangalore Medical College)', type: 'hospital', lat: 12.9642, lon: 77.5746, address: 'Fort Road, Near City Market, Bengaluru', phone: '080-26701150' },
      { name: 'Bowring and Lady Curzon Hospital', type: 'hospital', lat: 12.9822, lon: 77.6056, address: 'Shivaji Nagar, Bengaluru', phone: '080-25591325' },
      { name: 'St. John’s Medical College Hospital', type: 'hospital', lat: 12.9304, lon: 77.6186, address: 'Sarjapur Road, John Nagar, Bengaluru', phone: '080-22065000' },
    ],
  },
  Kolkata: {
    lat: 22.5726,
    lon: 88.3639,
    state: 'West Bengal',
    centers: [
      { name: 'Calcutta School of Tropical Medicine', type: 'hospital', lat: 22.5735, lon: 88.3615, address: '108 Chittaranjan Ave, Kolkata', phone: '033-22123695' },
      { name: 'SSKM Hospital (IPGMER)', type: 'hospital', lat: 22.5394, lon: 88.3431, address: '244 AJC Bose Road, Kolkata', phone: '033-22231589' },
    ],
  },
};

// Haversine formula for distance in km
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return (R * c).toFixed(1);
}

export default function NearbyCareView() {
  const [currentPos, setCurrentPos] = useState({ lat: 20.2961, lon: 85.8245 }); // Default Bhubaneswar
  const [locationDenied, setLocationDenied] = useState(false);
  const [locationLoading, setLocationLoading] = useState(true);
  const [searchCity, setSearchCity] = useState('Bhubaneswar');
  const [customSearchQuery, setCustomSearchQuery] = useState('');
  const [facilities, setFacilities] = useState([]);
  const [loadingFacilities, setLoadingFacilities] = useState(false);
  const [overpassError, setOverpassError] = useState(null);

  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  // Request browser geolocation
  const requestGeolocation = () => {
    setLocationLoading(true);
    setLocationDenied(false);

    if (!('geolocation' in navigator)) {
      setLocationDenied(true);
      setLocationLoading(false);
      loadFacilitiesForCoords(currentPos.lat, currentPos.lon, 'Bhubaneswar');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const coords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setCurrentPos(coords);
        setLocationLoading(false);
        setLocationDenied(false);
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setView([coords.lat, coords.lon], 13);
        }
        loadFacilitiesForCoords(coords.lat, coords.lon, 'My Location');
      },
      (err) => {
        console.warn('Geolocation denied or failed:', err);
        setLocationDenied(true);
        setLocationLoading(false);
        loadFacilitiesForCoords(currentPos.lat, currentPos.lon, 'Bhubaneswar');
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const initialLat = currentPos.lat;
    const initialLon = currentPos.lon;
    const map = L.map(mapContainerRef.current).setView([initialLat, initialLon], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors',
    }).addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    markersLayerRef.current = markersLayer;

    // Detect browser geolocation on mount
    requestGeolocation();

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch facilities from Overpass API or fallback preset
  const loadFacilitiesForCoords = async (lat, lon, cityName = 'Current Area') => {
    setLoadingFacilities(true);
    setOverpassError(null);

    // Update map center
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lat, lon], 13);
    }

    // Clear previous markers
    if (markersLayerRef.current) {
      markersLayerRef.current.clearLayers();
    }

    // Add user marker
    if (markersLayerRef.current) {
      L.marker([lat, lon], { icon: userIcon })
        .bindPopup(`<b>Your Selected Location</b><br/>${cityName}`)
        .addTo(markersLayerRef.current);
    }

    const overpassQuery = `
      [out:json][timeout:12];
      (
        node["amenity"="hospital"](around:10000,${lat},${lon});
        node["amenity"="clinic"](around:10000,${lat},${lon});
        node["amenity"="doctors"](around:10000,${lat},${lon});
        node["healthcare"="dermatologist"](around:10000,${lat},${lon});
      );
      out body 25;
    `;

    try {
      const response = await fetch('https://overpass-api.de/api/interpreter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `data=${encodeURIComponent(overpassQuery)}`,
      });

      if (!response.ok) throw new Error(`Overpass status ${response.status}`);

      const data = await response.json();
      const elements = data.elements || [];

      if (elements.length > 0) {
        const fetchedList = elements
          .filter((el) => el.tags && (el.tags.name || el.tags['name:en']))
          .map((el) => {
            const name = el.tags.name || el.tags['name:en'] || 'Medical Center';
            const type = el.tags.amenity || el.tags.healthcare || 'clinic';
            const street = el.tags['addr:street'] || el.tags['addr:suburb'] || el.tags['addr:city'] || '';
            const phone = el.tags.phone || el.tags['contact:phone'] || '108 (Emergency)';
            const dist = calculateDistance(lat, lon, el.lat, el.lon);

            return {
              name,
              type: type === 'hospital' ? 'hospital' : 'clinic',
              lat: el.lat,
              lon: el.lon,
              address: street || `${dist} km away`,
              phone,
              distance: dist,
            };
          })
          .sort((a, b) => parseFloat(a.distance) - parseFloat(b.distance));

        setFacilities(fetchedList.slice(0, 15));
        renderMarkers(fetchedList.slice(0, 15));
        setLoadingFacilities(false);
        return;
      }
    } catch (err) {
      console.warn('Overpass API query failed, falling back to local directory:', err);
      setOverpassError('OpenStreetMap Overpass API is slow or offline. Displaying verified regional public hospitals.');
    }

    // Fallback: use preset centers for nearest or chosen city
    const matchedPreset = PRESET_CITIES[searchCity] || PRESET_CITIES['Bhubaneswar'];
    const fallbackList = (matchedPreset.centers || []).map((c) => ({
      ...c,
      distance: calculateDistance(lat, lon, c.lat, c.lon),
    }));

    setFacilities(fallbackList);
    renderMarkers(fallbackList);
    setLoadingFacilities(false);
  };

  // Render facility markers on map
  const renderMarkers = (list) => {
    if (!markersLayerRef.current) return;

    list.forEach((f) => {
      const icon = f.type === 'hospital' ? hospitalIcon : clinicIcon;
      const marker = L.marker([f.lat, f.lon], { icon }).addTo(markersLayerRef.current);

      const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lon}`;
      marker.bindPopup(`
        <div style="font-family: sans-serif; font-size: 13px;">
          <b style="color: #0f172a;">${f.name}</b><br/>
          <span style="color: #64748b;">${f.type.toUpperCase()} • ${f.distance} km away</span><br/>
          <p style="margin: 4px 0; color: #334155;">${f.address}</p>
          <div style="margin-top: 6px;">
            <a href="tel:${f.phone.replace(/[^0-9]/g, '')}" style="color: #2563eb; font-weight: bold; text-decoration: none; margin-right: 12px;">📞 Call</a>
            <a href="${directionsUrl}" target="_blank" rel="noopener noreferrer" style="color: #059669; font-weight: bold; text-decoration: none;">📍 Directions</a>
          </div>
        </div>
      `);
    });
  };

  // Handle Preset City Button Click
  const handleSelectCity = (cityName) => {
    setSearchCity(cityName);
    const city = PRESET_CITIES[cityName];
    if (city) {
      setCurrentPos({ lat: city.lat, lon: city.lon });
      loadFacilitiesForCoords(city.lat, city.lon, cityName);
    }
  };

  // Custom text search via Nominatim
  const handleCustomSearch = async (e) => {
    e.preventDefault();
    if (!customSearchQuery.trim()) return;

    setLoadingFacilities(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          customSearchQuery + ', India'
        )}&limit=1`
      );
      const data = await res.json();
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        setCurrentPos({ lat, lon });
        setSearchCity(data[0].display_name.split(',')[0]);
        loadFacilitiesForCoords(lat, lon, data[0].display_name.split(',')[0]);
      } else {
        alert('Could not find that location. Please try entering a major district or city name.');
      }
    } catch {
      alert('Geocoding request failed. Please select one of the preset cities.');
    } finally {
      setLoadingFacilities(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* 1. National Emergency Header & SOS Banner */}
      <section className="bg-red-50 border-2 border-red-500 rounded-2xl p-4 sm:p-6 mb-6 shadow-sm">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-red-600 rounded-2xl flex items-center justify-center text-white shrink-0 shadow-md">
              <ShieldAlert className="w-8 h-8 animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black text-red-950 flex items-center gap-2">
                Emergency & Nearby Medical Care
              </h1>
              <p className="text-sm text-red-800">
                If you have severe pain, sudden bleeding, or difficulty breathing, contact emergency services immediately.
              </p>
            </div>
          </div>

          {/* Large SOS Button (Opens Phone Dialer to 112) */}
          <a
            href="tel:112"
            className="w-full md:w-auto px-8 py-4 bg-red-600 hover:bg-red-700 active:scale-95 text-white font-black text-lg rounded-xl shadow-lg hover:shadow-xl flex items-center justify-center gap-3 transition-all cursor-pointer text-center"
            aria-label="Call National Emergency 112"
          >
            <PhoneCall className="w-6 h-6 animate-bounce" />
            <span>SOS: CALL 112</span>
          </a>
        </div>

        {/* India Emergency Numbers Row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-red-200">
          <a
            href="tel:108"
            className="flex items-center justify-between p-3 bg-white border border-red-300 rounded-xl hover:bg-red-50 transition cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-red-600" />
              <div>
                <div className="font-bold text-slate-900">108 Ambulance</div>
                <div className="text-xs text-slate-500">24x7 Emergency Response (Free)</div>
              </div>
            </div>
            <span className="text-red-700 font-bold text-sm bg-red-100 px-2 py-1 rounded-md">Dial 108</span>
          </a>

          <a
            href="tel:102"
            className="flex items-center justify-between p-3 bg-white border border-red-300 rounded-xl hover:bg-red-50 transition cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <Hospital className="w-5 h-5 text-emerald-600" />
              <div>
                <div className="font-bold text-slate-900">102 Health Support</div>
                <div className="text-xs text-slate-500">Maternal & Child Health Care</div>
              </div>
            </div>
            <span className="text-emerald-700 font-bold text-sm bg-emerald-100 px-2 py-1 rounded-md">Dial 102</span>
          </a>

          <a
            href="tel:112"
            className="flex items-center justify-between p-3 bg-white border border-red-300 rounded-xl hover:bg-red-50 transition cursor-pointer"
          >
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-blue-600" />
              <div>
                <div className="font-bold text-slate-900">112 National Helpline</div>
                <div className="text-xs text-slate-500">Police, Fire & Medical Unified</div>
              </div>
            </div>
            <span className="text-blue-700 font-bold text-sm bg-blue-100 px-2 py-1 rounded-md">Dial 112</span>
          </a>
        </div>
      </section>

      {/* 2. Geolocation Status / Fallback Search Controls */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 mb-6 shadow-sm">
        {locationDenied && (
          <div className="flex items-center gap-3 p-3 mb-4 bg-amber-50 border border-amber-300 rounded-xl text-amber-900 text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            <div>
              <strong>Location Access Disabled:</strong> Browser location permission was denied or unavailable.
              Showing facilities for <strong>{searchCity}</strong>. You can switch cities or search below.
            </div>
          </div>
        )}

        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
          {/* Quick Indian City Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Quick Cities:</span>
            {Object.keys(PRESET_CITIES).map((city) => (
              <button
                key={city}
                onClick={() => handleSelectCity(city)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                  searchCity === city
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {city}
              </button>
            ))}
          </div>

          {/* Current GPS Trigger & Search Box */}
          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            <button
              onClick={requestGeolocation}
              disabled={locationLoading}
              className="flex items-center gap-2 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold transition cursor-pointer shrink-0"
              title="Use my GPS location"
            >
              <Crosshair className={`w-4 h-4 text-blue-600 ${locationLoading ? 'animate-spin' : ''}`} />
              <span>{locationLoading ? 'Locating...' : 'Use My GPS'}</span>
            </button>

            <form onSubmit={handleCustomSearch} className="flex items-center gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Search city/district (e.g. Pune)..."
                value={customSearchQuery}
                onChange={(e) => setCustomSearchQuery(e.target.value)}
                className="px-3 py-1.5 border border-slate-300 rounded-xl text-xs text-slate-800 focus:outline-blue-600 w-full sm:w-56"
              />
              <button
                type="submit"
                disabled={loadingFacilities}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold flex items-center gap-1 transition cursor-pointer"
              >
                <Search className="w-3.5 h-3.5" />
                <span>Find</span>
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* 3. Interactive Map & Facilities Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map Column (2 spans on desktop) */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="p-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs font-bold text-slate-700">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-red-600" />
                <span>OpenStreetMap Healthcare Centers (Within 10 km)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-600 inline-block"></span> Hospital
                </span>
                <span className="flex items-center gap-1 text-slate-600">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block"></span> Clinic/Doctor
                </span>
              </div>
            </div>

            {/* Leaflet Map Div */}
            <div ref={mapContainerRef} className="w-full h-96 sm:h-[480px] z-0" tabIndex={0} />
          </div>

          {overpassError && (
            <p className="text-xs text-slate-500 mt-2 italic flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
              {overpassError}
            </p>
          )}
        </div>

        {/* Facilities List Column (1 span on desktop) */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm h-full flex flex-col">
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-100">
              <h2 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                <Hospital className="w-4 h-4 text-blue-600" />
                <span>Nearby Facilities ({facilities.length})</span>
              </h2>
              {loadingFacilities && <span className="text-xs text-blue-600 font-semibold animate-pulse">Loading...</span>}
            </div>

            <div className="space-y-3 overflow-y-auto max-h-[440px] pr-1">
              {facilities.length === 0 && !loadingFacilities && (
                <div className="p-6 text-center text-slate-500 text-xs">
                  No medical facilities found in this exact radius. Try selecting a nearby district capital above.
                </div>
              )}

              {facilities.map((fac, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-slate-900 text-xs sm:text-sm leading-tight">{fac.name}</h3>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase shrink-0 ${
                          fac.type === 'hospital' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {fac.type}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2">{fac.address}</p>
                    <div className="text-[11px] font-semibold text-blue-700 mt-1">📍 {fac.distance} km away</div>
                  </div>

                  <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-200">
                    <a
                      href={`tel:${fac.phone.replace(/[^0-9]/g, '')}`}
                      className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer"
                    >
                      <PhoneCall className="w-3.5 h-3.5" />
                      <span>Call</span>
                    </a>
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${fac.lat},${fac.lon}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer"
                    >
                      <Navigation className="w-3.5 h-3.5" />
                      <span>Directions</span>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
