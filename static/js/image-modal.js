document.addEventListener('DOMContentLoaded', function() {
    // Get the modal and modal image elements
    const modal = document.getElementById('imageModal');
    const modalImg = document.getElementById('modalImage');

    // Get all clickable images
    const images = document.querySelectorAll('.clickable-image');
    
    // Add click event to each image
    images.forEach(img => {
        img.style.cursor = 'pointer';
        img.addEventListener('click', function(event) {
            // Stop the event from bubbling up (prevents card flip)
            event.stopPropagation();
            
            console.log('Image clicked, opening modal');
            
            // Show modal with the clicked image
            modal.style.display = "block";
            modalImg.src = this.getAttribute('data-full-img');
        });
    });

    // Get the <span> element that closes the modal
    const closeBtn = document.querySelector(".close-modal");

    // When the user clicks on <span> (x), close the modal
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal image, close it
    modal.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    }
    
    // Close the modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && modal.style.display === "block") {
            modal.style.display = "none";
        }
    });

    console.log('Image modal script loaded, found ' + images.length + ' clickable images');
});