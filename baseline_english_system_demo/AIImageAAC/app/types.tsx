export enum BoxType {
    TalkBox,
    OptionBox,
    GenericBox,
    FolderBox
}

export interface BoxInfo {
    id: number;
    type: BoxType;
    text: string;
    image: string;
    color: string;
    folderId?: string; //uuid
}

export interface FolderInfo {
    uuid: string;
    text: string;
    containedBoxes: BoxInfo[];
}

export interface AppSettings {
    boxMargin: number;
    numHorizontalBoxes: number;
    editLongPressDuration: number;
    allowExpansion: boolean;
    lockEditing: boolean;
}