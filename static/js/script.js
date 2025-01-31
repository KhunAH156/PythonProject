document.getElementById("QrGenerateForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        const data = await response.json();
        if (response.ok) {
            document.getElementById("result").innerHTML = `
                <p>Key ID: ${data.key_id}</p>
                <img src="${data.qr_code_path}" alt="QR Code" style="max-width: 200px;">
            `;
        } else {
            document.getElementById("result").innerText = `Error: ${data.error}`;
        }
    } catch (error) {
        document.getElementById("result").innerText = `Error: ${error.message}`;
    }
});
