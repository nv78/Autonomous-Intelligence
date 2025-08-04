export default function SampleProject(props) {
  return (
    <div className={"LP-Sample-Projects-Project"}>
      <div className={"LP-Sample-Projects-Project-Top "}>
        <div className={"LP-Sample-Projects-Project-Video"}>
          <iframe
            src={props.videoUrl}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            title="Embedded youtube"
            preload="auto"
            loading="lazy"
            className="rounded-2xl border-2 border-gray-900"
          />
        </div>
        <div
          className={
            "LP-Sample-Projects-Project-Description bg-[#141414] rounded-2xl"
          }
        >
          <h1>{props.title}</h1>
          <h3 className="LP-SubHeader">{props.sector}</h3>
          <h4 className="LP-SubTitle">{props.capability}</h4>
          <span className="LP-Text">{props.description}</span>
        </div>
      </div>
      {/* <div className={"LP-Sample-Projects-Project-Bottom"}>
        <img src={props.bottomImg} loading="lazy" />
      </div> */}
    </div>
  );
}
