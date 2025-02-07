document.addEventListener("DOMContentLoaded", async () => {
    const qrCodeList = document.getElementById("qrCodeList");

    try {
        const response = await fetch("/qrlist1");
        const data = await response.json();

        if (response.ok) {
            data.forEach(item => {
                const qrCard = document.createElement("div");
                qrCard.classList.add("qr-card");

                qrCard.innerHTML = `
                    <h2>QR Key</h2>
                    <img src="/static/qrcodes/${item.key_id}.png" alt="QR Code for ${item.key_id}">
                    <p>Key ID: ${item.key_id}</p>
                `;
                qrCodeList.appendChild(qrCard);
            });
        } else {
            qrCodeList.innerHTML = `<p>Error fetching QR codes: ${data.error}</p>`;
        }
    } catch (error) {
        qrCodeList.innerHTML = `<p>Error: ${error.message}</p>`;
    }
});