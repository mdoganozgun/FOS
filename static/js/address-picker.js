document.addEventListener("DOMContentLoaded", function () {
  const citySelect = document.getElementById("city");
  const districtSelect = document.getElementById("district");
  const neighborhoodSelect = document.getElementById("neighborhood");

  // Fetch cities from static JSON
  fetch("/static/data/sehirler.json")
    .then((res) => res.json())
    .then((cities) => {
      cities.forEach((city) => {
        const option = document.createElement("option");
        option.value = city.sehir_id;
        option.text = city.sehir_adi;
        citySelect.appendChild(option);
      });
    });

  // When a city is selected, load its districts
  citySelect.addEventListener("change", () => {
    const cityId = citySelect.value;
    districtSelect.innerHTML = '<option value="">Select District</option>';
    neighborhoodSelect.innerHTML = '<option value="">Select Neighborhood</option>';

    if (!cityId) return;

    fetch(`/api/districts/${cityId}`)
      .then((res) => res.json())
      .then((districts) => {
        districts.forEach((district) => {
          const option = document.createElement("option");
          option.value = district.ilce_id;
          option.text = district.ilce_adi;
          districtSelect.appendChild(option);
        });
      });
  });

  // Use event delegation for district selection
  document.addEventListener("change", function (event) {
    if (event.target && event.target.id === "district") {
      const districtId = event.target.value;
      neighborhoodSelect.innerHTML = '<option value="">Select Neighborhood</option>';

      if (!districtId) return;

      fetch(`/api/neighborhoods/${districtId}`)
        .then((res) => res.json())
        .then((neighborhoods) => {
          neighborhoods.forEach((n) => {
            const option = document.createElement("option");
            option.value = n.mahalle_adi;
            option.text = n.mahalle_adi;
            neighborhoodSelect.appendChild(option);
          });
        });
    }
  });
});