import { Tab, Tabs, TabList, TabPanel } from 'react-tabs';
import context from '../landing_page_assets/context.png';
import fewshotlearn from '../landing_page_assets/fewshotlearn.png';
import tabsynch from '../landing_page_assets/tabsynch.png';
import tabprogrammatic from '../landing_page_assets/tabprogrammatic.png';
import tabhuman from '../landing_page_assets/tabhuman.png';
import Select from 'react-select'
import { useState } from "react";

function CustomTab(props) {
    return <div className="LP-Home-Tab-Content">
        <div className="LP-Tab-Img">
            <img src={props.imgSrc} loading="lazy" />
        </div>
        <div className="LP-OverflowTab">
            <h3>{props.title}</h3>
            <div className={"LP-OverflowTab-Text"}>{props.description}</div>
            <div className={"LP-OverflowTab-Image"}>{props.img}</div>
        </div>
    </div>;
}

export default function CustomTabs() {

    var tab1 = <CustomTab title={<h3>Few Shot Learning</h3>} description={<h5>Utilize recent advances in few shot learning to label your data with minimal amounts of labeled examples<br></br><br></br>After you label just a few row of data, we are able to label the rest, using state of the art transformer models</h5>} imgSrc={fewshotlearn}></CustomTab>;
    var tab2 = <CustomTab title={<h3>Programmatic</h3>} description={<h5>Label your data programmatically using our powerful programmatic labeling functions<br></br><br></br>Heuristics such as key words, entities and regex expressions are fed into our initialized model</h5>} imgSrc={tabprogrammatic}></CustomTab>;
    var tab3 = <CustomTab title={<h3>Human In The Loop</h3>} description={<h5>Utilize a combination of human labeling from subject matter experts and machine labeling to achieve the most accurate results<br></br><br></br>We actively learn from the input of subject matter experts, who provide input into our model</h5>} imgSrc={tabhuman}></CustomTab>;
    var tab4 = <CustomTab className="tabTooBig" title={<h3>Synchronous</h3>} description={<h5>Get your data labeled in real time, rather than waiting for the output from data labelers<br></br><br>
    </br>Receive immediate feedback on the model's performance as you label your data, allowing you to make adjustments and fine-tune the model as needed</h5>} imgSrc={tabsynch}></CustomTab>;
    var tab5 = <CustomTab title={<h3>Contextual</h3>} description={<h5>Utilize transformer models and LLMs to label your data in a context-aware manner<br></br><br></br>Our large language models extract the context of words in sentences, not just the individual words themselves</h5>} imgSrc={context}></CustomTab>;


    const [selectedTab, setSelectedTab] = useState(0);

    var selectOptions = [
        { value: '0', label: 'Few Shot Learning' },
        { value: '1', label: 'Programmatic' },
        { value: '2', label: 'Human In The Loop' },
        { value: '3', label: 'Synchronous' },
        { value: '4', label: 'Contextual' }
      ];

      var selectedTabEl = [];
      if (selectedTab == 0) {
        selectedTabEl = [tab1];
      } else if(selectedTab == 1) {
        selectedTabEl = [tab2];
      } else if(selectedTab == 2) {
        selectedTabEl = [tab3];
      } else if(selectedTab == 3) {
        selectedTabEl = [tab4];
      } else if(selectedTab == 4) {
        selectedTabEl = [tab5];
      }


    return (
        <div>
            <Tabs className={"LP-Home-Tabs"}
                    selectedTabClassName="Background-Selected-Tab"
                    selectedTab={selectedTab}
                    >
                <div className="react-tabs__menu is--open">
                <TabList className={"LP-Home-Tabs-List"}>
                    <Tab>Few Shot Learning</Tab>
                    <Tab>Programmatic</Tab>
                    <Tab>Human In The Loop</Tab>
                    <Tab>Synchronous</Tab>
                    <Tab>Contextual</Tab>
                </TabList>
                </div>
                <TabPanel className="LP-Home-Tabs-Panel" index={0}>
                    {tab1}
                </TabPanel>
                <TabPanel className="LP-Home-Tabs-Panel" index={1}>
                    {tab2}
                </TabPanel>
                <TabPanel className="LP-Home-Tabs-Panel" index={2}>
                    {tab3}
                </TabPanel>
                <TabPanel className="LP-Home-Tabs-Panel" index={3}>
                    {tab4}
                </TabPanel>
                <TabPanel className="LP-Home-Tabs-Panel" index={4}>
                    {tab5}
                </TabPanel>
            </Tabs>
            <div className="LP-Home-Tabs-Small">
                <Select
                    className='my-react-select-container'
                    value={selectOptions[selectedTab]}
                    defaultValue={selectOptions[0]}
                    options={selectOptions}
                    onChange={(event) => setSelectedTab(event.value)}
                >
                    <option value={0}>Few Shot Learning</option>
                    <option value={1}>Programmatic</option>
                    <option value={2}>Human In The Loop</option>
                    <option value={3}>Synchronous</option>
                    <option value={4}>Contextual</option>
                </Select>
                {selectedTabEl}
        </div>
      </div>
)}