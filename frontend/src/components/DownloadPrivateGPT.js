import React from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faDownload } from "@fortawesome/free-solid-svg-icons";
import { faApple } from "@fortawesome/free-brands-svg-icons";

const DownloadPrivateGPT= () => {
  const downloadUrl = "https://anote-privategpt.s3.amazonaws.com/private_gpt-1.0.0-arm64.dmg";

  return (
    <div className="flex flex-col min-h-screen bg-[#141414]
">
      <div className="flex flex-grow items-center justify-center">
        <div className="pl-40 w-1/2 text-white flex flex-col justify-center" style={{ transform: 'translateY(-5%)' }}>
          <h1 className="text-4xl font-bold mb-4">🎉 Congratulations - Thank you for purchasing Panacea!</h1>
          <p className="mb-14">Welcome to Panacea! Engage with your documents directly on your device, ensuring your data remains private and secure. Experience a new level of smart, intuitive document interaction.</p>
          <div className="flex flex-col space-y-6 w-[50%]">
            <a href={downloadUrl} className="flex items-center justify-between bg-gradient-to-r from-[#306285] to-[#4caab9] hover:bg-blue-700 text-white font-bold py-3 px-4 rounded w-full" download>
              <FontAwesomeIcon icon={faApple} className="text-3xl px-3" />
              <div>Download App</div>
              <FontAwesomeIcon icon={faDownload} className="text-2xl px-3" />
            </a>
          </div>
        </div>
        <div className="flex-1 flex justify-end">
          <img
            src="/privategpt_photos/newprivategpt.png"
            alt="Screenshot"
            className="border-t-2 border-l-2 border-b-2 border-gray-600 rounded-tl-xl rounded-bl-xl max-h-[70vh]"
            style={{ boxShadow: '0 0 15px 1px rgba(103, 109, 117, 0.3)' }}
          />
        </div>
      </div>
    </div>
  );
}

export default DownloadPrivateGPT;
