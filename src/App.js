import React from 'react';
import './App.css';

class PictureDetails extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            headline: this.props.details.headline || "",
            description: this.props.details.headline || ""
        };

        this.handleChange = this.handleChange.bind(this);
    }

    static getDerivedStateFromProps(props, state) {
        if (!props.details) return state;
        return {
            headline: props.details.headline || "",
            description: props.details.description || ""
        };
    }

    handleChange(event) {
        this.setState({[event.target.name]: event.target.value});
        this.props.updatefn(this.props.file.name, event.target.name, event.target.value);
    }

    render() {
        return (
            <div className="picture-details-grid">
                <span>Name:</span> <span>{this.props.file.name}</span>
                <span>Headline:</span> <textarea className="small-textarea" name="headline" autoComplete="off" value={this.state.headline} onChange={this.handleChange} />
                <span>Description:</span> <textarea className="big-textarea" name="description" autoComplete="off" value={this.state.description} onChange={this.handleChange} />
            </div>
        );
    }
}

const Picture = (props) => {
    return (
        <React.Fragment>
            <img src={props.blobUrl}></img>
            <PictureDetails file={props.loadedFile} updatefn={props.updatefn} details={props.details} />
        </React.Fragment>
    );
}

class App extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            pictures: [],
            details: {},
            dirtyDetails: false  // 😳
        };
        this.loadPictures = this.loadPictures.bind(this);
        this.saveDetails = this.saveDetails.bind(this);
        this.loadDetails = this.loadDetails.bind(this);
        this.updateDetails = this.updateDetails.bind(this);
    }

    async loadPictures(event) {
        let newPictures = [];
        const dirHandle = await window.showDirectoryPicker();
        for await (const entry of dirHandle.values()) {
            if (!entry.name.endsWith(".jpg")) {
                continue;
            }
            const file = await entry.getFile();
            newPictures.push(file);
        }
        newPictures = newPictures.sort((a, b) => {
            if (a.name < b.name) return -1;
            if (a.name > b.name) return 1;
            return 0;
        });
        this.setState({pictures: newPictures});
    }

    async saveDetails() {
        const output = JSON.stringify(this.state.details);
        const options = {
            types: [{
                description: "JSON Files",
                accept: {
                    "application/json": [".json"]
                }
            }]
        };
        const handle = await window.showSaveFilePicker(options);
        const writeHandle = await handle.createWritable();
        await writeHandle.write(output);
        await writeHandle.close();
    }

    async loadDetails() {
        const [handle] = await window.showOpenFilePicker();
        const file = await handle.getFile();
        const detailsText = await file.text();
        this.setState({
            details: JSON.parse(detailsText),
            dirtyDetails: false
        });
        //this.forceUpdate();
    }

    updateDetails(file, key, value) {
        this.setState(prevState => {
            let details = Object.assign({}, prevState.details);
            if (!details.hasOwnProperty(file)) {
                details[file] = {};
            }
            details[file][key] = value;
            return {
                pictures: prevState.pictures,
                details: details,
                dirtyDetails: true
            };
        });
    }

    render() {
        const pictures = this.state.pictures.map((loadedFile) =>
            <Picture key={loadedFile.name} loadedFile={loadedFile} blobUrl={URL.createObjectURL(loadedFile)} details={this.state.details[loadedFile.name] || {}} updatefn={this.updateDetails} />
        );
        return (
          <div className="App">
              <button id="interact" disabled={this.state.pictures.length > 0} onClick={this.loadPictures}>Load photo folder</button>
              {this.state.pictures.length > 0 &&
              <>
                  <button id="saveDetails" disabled={!this.state.dirtyDetails} onClick={this.saveDetails}>Save text</button>
                  <button id="loadDetails" onClick={this.loadDetails}>Load text</button>
              </>
              }
              <div id="pictures" className="pictures-grid">{pictures}</div>
          </div>
        );
    }
}

export default App;
