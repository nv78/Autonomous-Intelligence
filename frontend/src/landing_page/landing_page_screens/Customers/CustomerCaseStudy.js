import React from 'react';
import DocViewer, { DocViewerRenderers } from '@cyntler/react-doc-viewer';
import { useLocation } from 'react-router-dom';

function CustomerCaseStudy() {
  const location = useLocation();
  const docUrl = location.state?.docUrl; // Extract the document URL from the navigation state

  const docs = [
    { uri: docUrl }
  ];

  return (
    <div className="flex justify-center items-center h-[64vh] max-h-[64vh] bg-[#141414]
 p-5 md:h-[180vh] md:max-h-[180vh]">
      <div className="w-full h-full md:max-w-4xl shadow-lg rounded-lg overflow-hidden">
        <DocViewer
        documents={docs}
        pluginRenderers={DocViewerRenderers}
        config={{
            header: {
              disableFileName: true,
              disableHeader: true,
            },
            pdfZoom: {
              defaultZoom: 1.1, // 1 as default,
              zoomJump: 0.2, // 0.1 as default,
            },
            pdfVerticalScrollByDefault: true, // false as default
          }}
          theme={{
            primary: "black",
            secondary: "#ffffff",
            tertiary: "#282E35",
            textPrimary: "#ffffff",
            textSecondary: "#5296d8",
            textTertiary: "#00000099",
            disableThemeScrollbar: false,
          }} />
      </div>
    </div>
  );
}

export default CustomerCaseStudy;
