import { Component, createSignal, useContext } from 'solid-js';
import { StoreContext, useCounter } from '../utils/store';

const Home: Component = () => {
  const [counter, { increment, decrement }] = useCounter();
  return (
    <>
      <p>{counter.count}</p>
      <button onClick={increment}>+</button>
      <button onClick={decrement}>-</button>
    </>
  );
};

export default Home
