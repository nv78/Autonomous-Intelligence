import React, { useState } from "react";
import Customer from "./Customer";


function Customers() {
  return (
    <div className="mb-24 py-20">
      <div className="mx-5 lg:mx-24">
      <div className="text-2xl sm:text-3xl lg:text-4xl my-15 text-center font-medium lg:font-bold text-white">
        Case Studies
      </div>
      <div class="p-10 grid grid-cols-1 sm:grid-cols-1 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-3 gap-5">
  <Customer
    image="/landing_page_assets/Answering Questions.png"
    title="10k"
    industry="Financial Services"
    description="Question Answering on 10-Ks"
  />
   <Customer
    image="/landing_page_assets/Generating Financial Reports.png"
    title="Workflows"
    industry="Financial Services"
    description="Generating Financial Reports"
  />
  <Customer
    image="/landing_page_assets/Summarizing Financial Statements.png"
    title="Know Your Customer"
    industry="Financial Services"
    description="Know Your Customer"
  />
</div>
      </div>
    </div>
  );
}

export default Customers;
