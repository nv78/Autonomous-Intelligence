import { combineReducers } from 'redux';
import { configureStore } from '@reduxjs/toolkit';
import { userSlice } from './../redux/UserSlice';
import storage from 'redux-persist/lib/storage';
import { persistReducer, persistStore } from 'redux-persist';

const persistConfig = {
    key: 'root',
    storage,
};

// Add new reducers the same way.
const rootReducer = combineReducers({
    userReducer: userSlice.reducer
});

const persistedReducer = persistReducer(persistConfig, rootReducer);

export const store = configureStore({
    reducer: persistedReducer
});

export const persistor = persistStore(store);