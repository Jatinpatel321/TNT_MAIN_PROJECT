import 'react-native-gesture-handler';
import { AppRegistry } from 'react-native';
import App from './App';
import firebase from '@react-native-firebase/app';

if (!firebase.apps.length) {
  firebase.initializeApp({
    apiKey: 'dummy-api-key',
    appId: 'dummy-app-id',
    projectId: 'dummy-project-id',
    databaseURL: 'https://dummy-db.firebaseio.com',
    messagingSenderId: '1234567890',
    storageBucket: 'dummy-project-id.appspot.com',
  });
}

AppRegistry.registerComponent('TNTVendorApp', () => App);