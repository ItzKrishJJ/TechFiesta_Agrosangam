document
  .getElementById("fetch-price-button")
  .addEventListener("click", function () {
    const state = document.querySelector("[name='State']").value;
    const district = document.querySelector("[name='District']").value;
    const crop = document.querySelector("[name='crop']").value;

    if (state && district && crop) {
      const apiUrl = `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=579b464db66ec23bdd0000010cef70382e7f44f74a72ad36e86cafdc&format=json&limit=5&filters[state.keyword]=${state}&fil579b464db66ec23bdd0000010cef70382e7f44f74a72ad36e86cafdcters[district]=${district}&filters[commodity]=${crop}`;

      console.log(`Fetching API URL: ${apiUrl}`);

      fetch(apiUrl)
        .then((response) => response.json())
        .then((data) => {
          console.log("API Response:", data);

          if (data.records && data.records.length > 0) {
            // Extract price from the response
            const price =
              data.records[0].modal_price ||
              data.records[0].min_price ||
              data.records[0].max_price;

            if (price) {
              document.getElementById("price_per_ton").value = price;
            } else {
              alert("Price data is missing in the API response.");
            }
          } else {
            alert("No price data found for the selected criteria.");
          }
        })
        .catch((error) => {
          console.error("Error fetching price:", error);
          alert("An error occurred while fetching the price.");
        });
    } else {
      alert("Please select all fields to fetch the price.");
    }
  });

// Delete Crop Functionality
function deleteCrop(cropId) {
  if (confirm("Are you sure you want to delete this crop?")) {
    fetch(`/delete_crop/${cropId}`, {
      method: "POST", // As per your existing route
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((response) => {
        if (response.redirected) {
          window.location.href = response.url; // Redirect to dashboard
        } else {
          alert("Failed to delete the crop.");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred while deleting the crop.");
      });
  }
}
